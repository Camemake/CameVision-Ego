// SPDX-License-Identifier: GPL-2.0
/*
 * Official DPHY bind + SET_CSI_IDX + v4l2_dev from CSI, then s_stream.
 * Late DPHY probe leaves sd.v4l2_dev NULL; stream-on needs it.
 */
#include <linux/device.h>
#include <linux/ioctl.h>
#include <linux/module.h>
#include <linux/of.h>
#include <media/v4l2-async.h>
#include <media/v4l2-mediabus.h>
#include <media/v4l2-subdev.h>

extern struct bus_type i2c_bus_type;
extern struct bus_type platform_bus_type;

#define DRV_SLOT 15
#define MBUS_FLAGS ((1u << 1) | (1u << 4) | (1u << 10))
#define RKCIF_MAX_CSI_NUM 4
#define PHY_VENDOR_INNO 0
#define BASE_VIDIOC_PRIVATE 192
#define RKCIF_CMD_SET_CSI_IDX _IOW('V', BASE_VIDIOC_PRIVATE + 7, struct rkcif_csi_info)

static unsigned long bound_fn;
module_param(bound_fn, ulong, 0444);

struct rkcif_csi_info {
	int csi_num;
	int csi_idx[RKCIF_MAX_CSI_NUM];
	int dphy_vendor[RKCIF_MAX_CSI_NUM];
};

struct sensor_async_subdev {
	struct v4l2_async_subdev asd;
	struct v4l2_mbus_config mbus;
	int lanes;
};

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

static void *find_notifier(void *sd)
{
	unsigned long p, start = (unsigned long)sd;

	if (!bound_fn || !sd)
		return NULL;
	for (p = start; p > start - 0x800; p -= 8) {
		unsigned long ops = *(unsigned long *)p;

		if (ops < 0xffffffc000000000UL)
			continue;
		if (*(unsigned long *)ops == bound_fn ||
		    *(unsigned long *)(ops + 8) == bound_fn)
			return (void *)p;
	}
	return NULL;
}

static void start_one(const char *cam_path, const char *dphy_path,
		      const char *csi_path, int csi_idx)
{
	struct device *cam_dev = find_of(&i2c_bus_type, cam_path);
	struct device *dphy_dev = find_of(&platform_bus_type, dphy_path);
	struct device *csi_dev = find_of(&platform_bus_type, csi_path);
	struct v4l2_subdev *dphy, *cam, *csi;
	struct rkcif_csi_info info = {0};
	struct sensor_async_subdev s = {0};
	int (*bound)(void *, void *, void *) = (void *)bound_fn;
	void *notifier;
	int ret;

	if (!cam_dev || !dphy_dev)
		goto put;
	cam = drvdata(cam_dev);
	dphy = drvdata(dphy_dev);
	csi = csi_dev ? drvdata(csi_dev) : NULL;
	info.csi_num = 1;
	info.csi_idx[0] = csi_idx;
	info.dphy_vendor[0] = PHY_VENDOR_INNO;
	ret = v4l2_subdev_call(dphy, core, ioctl, RKCIF_CMD_SET_CSI_IDX, &info);
	pr_info("mstart: %s set_csi_idx %d -> %d\n", dphy_path, csi_idx, ret);
	notifier = find_notifier(dphy);
	if (notifier && bound) {
		s.mbus.type = V4L2_MBUS_CSI2_DPHY;
		s.mbus.bus.mipi_csi2.flags = MBUS_FLAGS;
		s.mbus.bus.mipi_csi2.num_data_lanes = 2;
		s.lanes = 2;
		ret = bound(notifier, cam, &s.asd);
		pr_info("mstart: %s bound %d\n", dphy_path, ret);
	}
	if (!dphy->v4l2_dev)
		dphy->v4l2_dev = (csi && csi->v4l2_dev) ? csi->v4l2_dev : cam->v4l2_dev;
	ret = v4l2_subdev_call(dphy, video, s_stream, 1);
	pr_info("mstart: %s s_stream %d v4l2_dev=%px\n", dphy_path, ret, dphy->v4l2_dev);
put:
	if (cam_dev)
		put_device(cam_dev);
	if (dphy_dev)
		put_device(dphy_dev);
	if (csi_dev)
		put_device(csi_dev);
}

static int __init mstart_init(void)
{
	start_one("/i2c@21120000/sc233hgs@30", "/csi2-dphy0", "/mipi0-csi2", 0);
	start_one("/i2c-gpio-cam1/sc233hgs@30", "/csi2-dphy3", "/mipi2-csi2", 2);
	return 0;
}

static void __exit mstart_exit(void)
{
}

module_init(mstart_init);
module_exit(mstart_exit);
MODULE_LICENSE("GPL");
