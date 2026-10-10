// SPDX-License-Identifier: GPL-2.0
/*
 * Link MIRA220 subdevs onto the CIF media graphs. No private-struct pokes.
 */
#include <linux/device.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/stddef.h>
#include <linux/string.h>
#include <media/media-device.h>
#include <media/media-entity.h>
#include <media/v4l2-mediabus.h>
#include <media/v4l2-subdev.h>

#define MBUS_FLAGS ((1u << 1) | (1u << 4) | (1u << 10))

extern struct bus_type i2c_bus_type;
extern struct bus_type platform_bus_type;

#define DRV_SLOT 15

static int kptr(const void *p)
{
	unsigned long v = (unsigned long)p;

	return v >= 0xffffff8000000000UL;
}

static struct device *find_of(struct bus_type *bus, const char *path)
{
	struct device_node *np = of_find_node_by_path(path);
	struct device *dev;

	if (!np)
		return NULL;
	dev = bus_find_device_by_of_node(bus, np);
	of_node_put(np);
	return dev;
}

static void *drvdata(struct device *dev)
{
	return ((void **)dev)[DRV_SLOT];
}

static struct media_entity *entity_named(void *priv, const char *want)
{
	unsigned long p;
	unsigned long start = (unsigned long)priv;

	if (!kptr(priv))
		return NULL;
	for (p = start; p < start + 0x1000; p += 8) {
		const char *s = *(const char **)p;
		struct media_entity *e;

		if (!kptr(s) || strcmp(s, want))
			continue;
		e = (struct media_entity *)(p - offsetof(struct media_entity, name));
		if (e->num_pads > 0 && e->num_pads < 32 && kptr(e->pads))
			return e;
	}
	return NULL;
}

static int link_en(struct media_entity *src, int sp, struct media_entity *snk, int dp)
{
	int ret;

	if (!src || !snk)
		return -EINVAL;
	ret = media_create_pad_link(src, sp, snk, dp, MEDIA_LNK_FL_ENABLED);
	pr_info("miralink: link %s:%d -> %s:%d = %d\n",
		src->name, sp, snk->name, dp, ret);
	if (ret == -EEXIST) {
		struct media_link *link = media_entity_find_link(&src->pads[sp],
								 &snk->pads[dp]);

		if (link) {
			media_entity_setup_link(link, 0);
			ret = media_entity_setup_link(link, MEDIA_LNK_FL_ENABLED);
			pr_info("miralink: relink %s:%d -> %s:%d = %d\n",
				src->name, sp, snk->name, dp, ret);
		}
	}
	return ret;
}

static void wire_one(struct media_entity *cam, struct device *dphy_dev,
		     struct device *csi_dev, const char *dphy_name)
{
	void *dphy_priv, *csi_priv;
	struct media_entity *dphy, *csi;
	struct media_device *mdev;
	int ret;

	if (!cam || !dphy_dev || !csi_dev)
		return;
	dphy_priv = drvdata(dphy_dev);
	csi_priv = drvdata(csi_dev);
	dphy = entity_named(dphy_priv, dphy_name);
	csi = entity_named(csi_priv, "rockchip-mipi-csi2");
	if (!dphy || !csi) {
		pr_err("miralink: no entity dphy=%px (%s) csi=%px\n",
		       dphy, dphy_name, csi);
		return;
	}
	mdev = csi->graph_obj.mdev;
	if (!kptr(mdev)) {
		pr_err("miralink: %s no mdev\n", dphy_name);
		return;
	}
	if (!cam->graph_obj.mdev) {
		ret = media_device_register_entity(mdev, cam);
		pr_info("miralink: add %s %d\n", cam->name, ret);
	}
	if (!dphy->graph_obj.mdev) {
		ret = media_device_register_entity(mdev, dphy);
		pr_info("miralink: add %s %d\n", dphy->name, ret);
	}
	link_en(cam, 0, dphy, 0);
	link_en(dphy, 1, csi, 0);
	/* Point DPHY/CSI at the sensor so stream setup can see a terminal. */
	{
		unsigned long *q = dphy_priv;
		char *b = dphy_priv;

		if (q[0x290 / 8] == 0) {
			q[0x290 / 8] = (unsigned long)cam;
			*(u32 *)(b + 0x298) = V4L2_MBUS_CSI2_DPHY;
			*(u32 *)(b + 0x29c) = MBUS_FLAGS;
			pr_info("miralink: dphy sensors0=%px\n", cam);
		}
	}
	{
		unsigned long *q = csi_priv;
		char *b = csi_priv;
		int i, src = -1;

		for (i = 0; i < 0x800 / 8; i++) {
			if ((void *)q[i] == dphy) {
				src = i;
				break;
			}
		}
		if (src >= 0 && src + 3 < 0x800 / 8 && q[src + 3] == 0) {
			q[src + 3] = (unsigned long)cam;
			*(u32 *)(b + (src + 3) * 8 + 8) = V4L2_MBUS_CSI2_DPHY;
			*(u32 *)(b + (src + 3) * 8 + 12) = MBUS_FLAGS;
			*(int *)(b + (src + 3) * 8 + 16) = 2;
			pr_info("miralink: csi sensors0 @%03x\n", (src + 3) * 8);
		} else {
			pr_info("miralink: csi src_sd slot %d\n", src);
		}
	}
}

static int __init miralink_init(void)
{
	struct device *cam0, *cam1, *d0, *d3, *csi0, *csi2;
	struct media_entity *e_cam0, *e_cam1;

	cam0 = find_of(&i2c_bus_type, "/i2c@21120000/sc233hgs@30");
	cam1 = find_of(&i2c_bus_type, "/i2c-gpio-cam1/sc233hgs@30");
	d0 = find_of(&platform_bus_type, "/csi2-dphy0");
	d3 = find_of(&platform_bus_type, "/csi2-dphy3");
	csi0 = find_of(&platform_bus_type, "/mipi0-csi2");
	csi2 = find_of(&platform_bus_type, "/mipi2-csi2");
	if (!cam0 || !d0 || !csi0) {
		pr_err("miralink: missing cam0=%px d0=%px csi0=%px\n", cam0, d0, csi0);
		return 0;
	}
	e_cam0 = drvdata(cam0);
	e_cam1 = cam1 ? drvdata(cam1) : NULL;
	if (!kptr(e_cam0)) {
		pr_err("miralink: cam0 drvdata %px\n", e_cam0);
		goto out;
	}
	pr_info("miralink: cam0=%s cam1=%s\n",
		e_cam0->name, e_cam1 ? e_cam1->name : "none");
	wire_one(e_cam0, d0, csi0, "rockchip-csi2-dphy0");
	if (e_cam1 && d3 && csi2)
		wire_one(e_cam1, d3, csi2, "rockchip-csi2-dphy3");
out:
	put_device(cam0);
	if (cam1)
		put_device(cam1);
	put_device(d0);
	if (d3)
		put_device(d3);
	put_device(csi0);
	if (csi2)
		put_device(csi2);
	return 0;
}

static void __exit miralink_exit(void)
{
}

module_init(miralink_init);
module_exit(miralink_exit);
MODULE_LICENSE("GPL");
