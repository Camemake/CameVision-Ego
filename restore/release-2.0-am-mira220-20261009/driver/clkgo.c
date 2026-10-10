// SPDX-License-Identifier: GPL-2.0
/*
 * Enable MIPI/CAM output clocks via real kernel symbols from kallsyms.
 */
#include <linux/module.h>
#include <linux/kernel.h>

static unsigned long lookup_fn;
static unsigned long set_fn;
static unsigned long en_fn;
module_param(lookup_fn, ulong, 0444);
module_param(set_fn, ulong, 0444);
module_param(en_fn, ulong, 0444);

static int kick(const char *name, unsigned long hz)
{
	void *(*lookup)(const char *) = (void *)lookup_fn;
	int (*set)(void *, unsigned long) = (void *)set_fn;
	int (*en)(void *) = (void *)en_fn;
	void *clk;
	int ret;

	if (!lookup || !set || !en) {
		pr_err("clkgo: missing kallsyms\n");
		return -EINVAL;
	}
	clk = lookup(name);
	if (!clk) {
		pr_err("clkgo: no %s\n", name);
		return -ENOENT;
	}
	ret = set(clk, hz);
	pr_info("clkgo: %s set %lu -> %d\n", name, hz, ret);
	ret = en(clk);
	pr_info("clkgo: %s enable -> %d\n", name, ret);
	return ret;
}

static int __init clkgo_init(void)
{
	static const char *const names[] = {
		"clk_mipi0_out2io",
		"clk_mipi1_out2io",
		"clk_mipi2_out2io",
		"clk_mipi3_out2io",
		"clk_cam0_out",
		"clk_cam1_out",
	};
	int i;

	for (i = 0; i < ARRAY_SIZE(names); i++)
		kick(names[i], 38400000);
	return 0;
}

static void __exit clkgo_exit(void)
{
}

module_init(clkgo_init);
module_exit(clkgo_exit);
MODULE_LICENSE("GPL");
