// SPDX-License-Identifier: GPL-2.0
/*
 * Real CSI layout from dump: format_mbus @0x508, crop @0x538, src_sd @0x550.
 * sensors[0] follows sink_linked[] at 0x568.
 */
#include <linux/device.h>
#include <linux/module.h>
#include <linux/of.h>
#include <media/v4l2-mediabus.h>

extern struct bus_type i2c_bus_type;
extern struct bus_type platform_bus_type;

#define DRV_SLOT 15
#define MBUS_FLAGS ((1u << 1) | (1u << 4) | (1u << 10))

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

static void fill_csi(void *sd, void *cam)
{
	char *b = sd;
	unsigned long *q = sd;

	if (!sd || !cam)
		return;
	if (q[0x568 / 8] == 0)
		q[0x568 / 8] = (unsigned long)cam;
	*(u32 *)(b + 0x570) = V4L2_MBUS_CSI2_DPHY;
	*(u32 *)(b + 0x574) = MBUS_FLAGS;
	if (*(int *)(b + 0x578) == 0)
		*(int *)(b + 0x578) = 2;
	if (*(int *)(b + 0x598) == 0)
		*(int *)(b + 0x598) = 1;
	pr_info("mfix4: sen=%px src=%px type=%u\n",
		(void *)q[0x568 / 8], (void *)q[0x550 / 8], *(u32 *)(b + 0x570));
}

static int __init mfix4_init(void)
{
	struct device *cam0, *cam1, *csi0, *csi2;

	cam0 = find_of(&i2c_bus_type, "/i2c@21120000/sc233hgs@30");
	cam1 = find_of(&i2c_bus_type, "/i2c-gpio-cam1/sc233hgs@30");
	csi0 = find_of(&platform_bus_type, "/mipi0-csi2");
	csi2 = find_of(&platform_bus_type, "/mipi2-csi2");
	if (!cam0 || !csi0)
		return 0;
	fill_csi(drvdata(csi0), drvdata(cam0));
	if (cam1 && csi2)
		fill_csi(drvdata(csi2), drvdata(cam1));
	put_device(cam0);
	if (cam1)
		put_device(cam1);
	put_device(csi0);
	if (csi2)
		put_device(csi2);
	return 0;
}

static void __exit mfix4_exit(void)
{
}

module_init(mfix4_init);
module_exit(mfix4_exit);
MODULE_LICENSE("GPL");
