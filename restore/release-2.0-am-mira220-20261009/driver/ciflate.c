// SPDX-License-Identifier: GPL-2.0
/*
 * Call the builtin DPHY/CSI2/CIF register functions after mira220.
 * Addresses come from /proc/kallsyms — those symbols are not exported.
 */
#include <linux/module.h>
#include <linux/kernel.h>

static unsigned long dphy_init;
static unsigned long csi2_init;
static unsigned long rkcif_init;
module_param(dphy_init, ulong, 0444);
module_param(csi2_init, ulong, 0444);
module_param(rkcif_init, ulong, 0444);

static int call_init(const char *name, unsigned long addr)
{
	int (*fn)(void);
	int ret;

	if (!addr) {
		pr_info("ciflate: %s skipped\n", name);
		return 0;
	}
	fn = (int (*)(void))addr;
	ret = fn();
	pr_info("ciflate: %s @%px -> %d\n", name, (void *)addr, ret);
	return ret;
}

static int __init ciflate_init(void)
{
	call_init("dphy", dphy_init);
	call_init("csi2", csi2_init);
	call_init("rkcif", rkcif_init);
	return 0;
}

static void __exit ciflate_exit(void)
{
}

module_init(ciflate_init);
module_exit(ciflate_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Late CIF/DPHY probe after MIRA220");
