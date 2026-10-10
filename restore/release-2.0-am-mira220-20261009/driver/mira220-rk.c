// SPDX-License-Identifier: GPL-2.0
/*
 * Rockchip V4L2 subdev for AMS MIRA220 on CameVision Ego (RV1126B).
 * Register list from the AMS V4L2 driver. Accepts 27 MHz or 38.4 MHz xvclk.
 */
#include <linux/clk.h>
#include <linux/delay.h>
#include <linux/ioctl.h>
#include <linux/kernel.h>
#include <linux/gpio/consumer.h>
#include <linux/of_clk.h>
#include <linux/pinctrl/consumer.h>
#include <linux/i2c.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_graph.h>
#include <linux/string.h>
#include <linux/pm_runtime.h>
#include <linux/regulator/consumer.h>
#include <linux/version.h>
#include "rk-camera-module.h"
#include <media/v4l2-ctrls.h>
#include <media/v4l2-dev.h>
#include <media/v4l2-device.h>
#include <media/v4l2-fwnode.h>
#include <media/v4l2-mediabus.h>
#include <media/v4l2-subdev.h>

#include "mira220_init.h"

#define DRIVER_VERSION KERNEL_VERSION(0, 0x01, 0x00)
#define MIRA220_NAME "mira220"
#define MIRA220_W 1600
#define MIRA220_H 1400
#define MIRA220_LANES 2
#define MIRA220_LINK_FREQ 750000000
#define MIRA220_PIXEL_RATE 384000000
#define OF_CAMERA_HDR_MODE "rockchip,camera-hdr-mode"

static const char *const mira220_supply_names[] = {
	"avdd",
	"dovdd",
	"dvdd",
};

struct mira220 {
	struct i2c_client *client;
	struct clk *xvclk;
	struct gpio_desc *reset_gpio;
	struct gpio_desc *pwdn_gpio;
	struct regulator_bulk_data supplies[ARRAY_SIZE(mira220_supply_names)];
	struct v4l2_subdev subdev;
	struct v4l2_device v4l2_dev;
	bool own_v4l2;
	struct media_pad pad;
	struct v4l2_ctrl_handler ctrl_handler;
	struct v4l2_mbus_framefmt fmt;
	u32 module_index;
	const char *module_facing;
	const char *module_name;
	const char *len_name;
	struct v4l2_ctrl *exposure;
	struct v4l2_ctrl *again;
	u16 exp_reg;
	u16 gain_reg;
	bool streaming;
	bool power_on;
};

static inline struct mira220 *to_mira220(struct v4l2_subdev *sd)
{
	return container_of(sd, struct mira220, subdev);
}

static int mira220_write(struct mira220 *m, u16 addr, u8 val)
{
	u8 buf[3] = { addr >> 8, addr & 0xff, val };
	struct i2c_msg msg = {
		.addr = m->client->addr,
		.flags = 0,
		.len = 3,
		.buf = buf,
	};
	int ret = i2c_transfer(m->client->adapter, &msg, 1);

	return ret == 1 ? 0 : (ret < 0 ? ret : -EIO);
}

static int mira220_write16(struct mira220 *m, u16 addr, u16 val)
{
	u8 buf[4] = { addr >> 8, addr & 0xff, val & 0xff, val >> 8 };
	struct i2c_msg msg = {
		.addr = m->client->addr,
		.flags = 0,
		.len = 4,
		.buf = buf,
	};
	int ret = i2c_transfer(m->client->adapter, &msg, 1);

	return ret == 1 ? 0 : (ret < 0 ? ret : -EIO);
}

static int mira220_load_init(struct mira220 *m)
{
	unsigned int i;
	int ret;

	for (i = 0; i < ARRAY_SIZE(mira220_init_regs); i++) {
		ret = mira220_write(m, mira220_init_regs[i].addr,
				    mira220_init_regs[i].val);
		if (ret)
			return ret;
	}
	ret = mira220_write(m, 0x6012, MIRA220_LANES - 1);
	if (ret)
		return ret;
	ret = mira220_write(m, 0x6013, 0x00);
	if (ret)
		return ret;
	ret = mira220_write(m, 0x209e, 0x04);
	if (ret)
		return ret;
	ret = mira220_write(m, 0x208d, 0x02);
	if (ret)
		return ret;
	ret = mira220_write16(m, 0x102b, 304);
	if (ret)
		return ret;
	/* AMS/RPi: VSTART/HSTART are the ROI origin, not gain.
	 * Full 1600x1400 is centered in the active array → (0,0).
	 */
	ret = mira220_write16(m, 0x107d, 0);
	if (ret)
		return ret;
	ret = mira220_write16(m, 0x200a, 0);
	if (ret)
		return ret;
	ret = mira220_write16(m, 0x1087, MIRA220_H);
	if (ret)
		return ret;
	/* AMS: HSIZE is width/2; MIPI_HSIZE is full width. */
	ret = mira220_write16(m, 0x2008, MIRA220_W / 2);
	if (ret)
		return ret;
	ret = mira220_write16(m, 0x207d, MIRA220_W);
	if (ret)
		return ret;
	return mira220_write16(m, 0x100c, m->exp_reg ? m->exp_reg : 1000);
}

static int mira220_start(struct mira220 *m)
{
	int ret;

	ret = mira220_write(m, 0x1003, 0x10);
	if (ret)
		return ret;
	ret = mira220_write(m, 0x1002, 0x04);
	if (ret)
		return ret;
	return mira220_write(m, 0x10f0, 0x01);
}

static int mira220_stop(struct mira220 *m)
{
	mira220_write(m, 0x1003, 0x02);
	return mira220_write(m, 0x10f0, 0x00);
}

static int mira220_power(struct mira220 *m, bool on)
{
	int ret;

	if (m->power_on == on)
		return 0;
	if (on) {
		ret = regulator_bulk_enable(ARRAY_SIZE(m->supplies), m->supplies);
		if (ret && ret != -ENODEV)
			dev_warn(&m->client->dev, "regulators %d\n", ret);
		if (!IS_ERR(m->xvclk)) {
			ret = clk_set_rate(m->xvclk, 27000000);
			if (ret)
				ret = clk_set_rate(m->xvclk, 38400000);
			if (ret)
				dev_warn(&m->client->dev,
					 "xvclk rate failed %d, using %lu\n",
					 ret, clk_get_rate(m->xvclk));
			ret = clk_prepare_enable(m->xvclk);
			if (ret)
				return ret;
		}
		if (!IS_ERR(m->pwdn_gpio))
			gpiod_set_value_cansleep(m->pwdn_gpio, 1);
		if (!IS_ERR(m->reset_gpio)) {
			gpiod_set_value_cansleep(m->reset_gpio, 1);
			usleep_range(1000, 2000);
			gpiod_set_value_cansleep(m->reset_gpio, 0);
		}
		msleep(120);
		m->power_on = true;
		return 0;
	}
	mira220_stop(m);
	if (!IS_ERR(m->reset_gpio))
		gpiod_set_value_cansleep(m->reset_gpio, 1);
	if (!IS_ERR(m->pwdn_gpio))
		gpiod_set_value_cansleep(m->pwdn_gpio, 0);
	if (!IS_ERR(m->xvclk))
		clk_disable_unprepare(m->xvclk);
	regulator_bulk_disable(ARRAY_SIZE(m->supplies), m->supplies);
	m->power_on = false;
	return 0;
}

static int mira220_s_power(struct v4l2_subdev *sd, int on)
{
	struct mira220 *m = to_mira220(sd);
	int ret = 0;

	return mira220_power(m, !!on);
}

static int mira220_s_stream(struct v4l2_subdev *sd, int on)
{
	struct mira220 *m = to_mira220(sd);
	int ret = 0;

	if (m->streaming == !!on)
		return 0;
	dev_info(&m->client->dev, "s_stream %d\n", on);
	if (on) {
		ret = mira220_power(m, true);
		if (ret)
			return ret;
		ret = mira220_load_init(m);
		if (ret) {
			dev_err(&m->client->dev, "init regs %d\n", ret);
			return ret;
		}
		ret = mira220_start(m);
		if (ret) {
			dev_err(&m->client->dev, "start %d\n", ret);
			return ret;
		}
		m->streaming = true;
	} else {
		mira220_stop(m);
		m->streaming = false;
	}
	return ret;
}

static int mira220_g_mbus_config(struct v4l2_subdev *sd, unsigned int pad,
				 struct v4l2_mbus_config *cfg)
{
	cfg->type = V4L2_MBUS_CSI2_DPHY;
	cfg->bus.mipi_csi2.num_data_lanes = MIRA220_LANES;
	cfg->bus.mipi_csi2.data_lanes[0] = 1;
	cfg->bus.mipi_csi2.data_lanes[1] = 2;
	/* Vendor CSI2 still reads the old mbus.flags lane bits at this offset. */
	cfg->bus.mipi_csi2.flags = (1u << 1) | (1u << 4) | (1u << 10);
	return 0;
}

static int mira220_enum_mbus_code(struct v4l2_subdev *sd,
				  struct v4l2_subdev_state *state,
				  struct v4l2_subdev_mbus_code_enum *code)
{
	if (code->index)
		return -EINVAL;
	code->code = MEDIA_BUS_FMT_SBGGR10_1X10;
	return 0;
}

static int mira220_enum_frame_sizes(struct v4l2_subdev *sd,
				    struct v4l2_subdev_state *state,
				    struct v4l2_subdev_frame_size_enum *fse)
{
	if (fse->index || fse->code != MEDIA_BUS_FMT_SBGGR10_1X10)
		return -EINVAL;
	fse->min_width = MIRA220_W;
	fse->max_width = MIRA220_W;
	fse->min_height = MIRA220_H;
	fse->max_height = MIRA220_H;
	return 0;
}

static int mira220_get_fmt(struct v4l2_subdev *sd,
			   struct v4l2_subdev_state *state,
			   struct v4l2_subdev_format *fmt)
{
	struct mira220 *m = to_mira220(sd);

	fmt->format = m->fmt;
	return 0;
}

static int mira220_set_fmt(struct v4l2_subdev *sd,
			   struct v4l2_subdev_state *state,
			   struct v4l2_subdev_format *fmt)
{
	struct mira220 *m = to_mira220(sd);

	fmt->format.width = MIRA220_W;
	fmt->format.height = MIRA220_H;
	fmt->format.code = MEDIA_BUS_FMT_SBGGR10_1X10;
	fmt->format.field = V4L2_FIELD_NONE;
	fmt->format.colorspace = V4L2_COLORSPACE_RAW;
	m->fmt = fmt->format;
	return 0;
}

static int mira220_g_frame_interval(struct v4l2_subdev *sd,
				    struct v4l2_subdev_frame_interval *fi)
{
	fi->interval.numerator = 1;
	fi->interval.denominator = 30;
	return 0;
}

static long mira220_ioctl(struct v4l2_subdev *sd, unsigned int cmd, void *arg)
{
	struct mira220 *m = to_mira220(sd);
	struct rkmodule_inf *inf;
	struct rkmodule_hdr_cfg *hdr;
	unsigned int nr = _IOC_NR(cmd);

	switch (cmd) {
	case RKMODULE_GET_MODULE_INFO:
	case_module_info:
		if (!arg)
			return -EINVAL;
		inf = arg;
		memset(inf, 0, _IOC_SIZE(cmd) ? min_t(unsigned int, _IOC_SIZE(cmd),
						      sizeof(*inf)) : sizeof(*inf));
		strscpy(inf->base.sensor, MIRA220_NAME, sizeof(inf->base.sensor));
		strscpy(inf->base.module, m->module_name, sizeof(inf->base.module));
		strscpy(inf->base.lens, m->len_name, sizeof(inf->base.lens));
		return 0;
	case RKMODULE_GET_HDR_CFG:
	case_hdr_get:
		if (!arg)
			return -EINVAL;
		hdr = arg;
		memset(hdr, 0, sizeof(*hdr));
		hdr->hdr_mode = NO_HDR;
		return 0;
	case RKMODULE_SET_HDR_CFG:
	case_hdr_set:
		return 0;
	case RKMODULE_SET_QUICK_STREAM:
	case_quick: {
		u32 *on = arg;

		return mira220_s_stream(sd, on ? *on : 0);
	}
	default:
		if (nr == _IOC_NR(RKMODULE_GET_MODULE_INFO))
			goto case_module_info;
		if (nr == _IOC_NR(RKMODULE_GET_HDR_CFG))
			goto case_hdr_get;
		if (nr == _IOC_NR(RKMODULE_SET_HDR_CFG))
			goto case_hdr_set;
		if (nr == _IOC_NR(RKMODULE_SET_QUICK_STREAM))
			goto case_quick;
		return -ENOIOCTLCMD;
	}
}

#ifdef CONFIG_COMPAT
static long mira220_compat_ioctl32(struct v4l2_subdev *sd, unsigned int cmd,
				   unsigned long arg)
{
	return -ENOIOCTLCMD;
}
#endif

static const struct v4l2_subdev_core_ops mira220_core_ops = {
	.s_power = mira220_s_power,
	.ioctl = mira220_ioctl,
#ifdef CONFIG_COMPAT
	.compat_ioctl32 = mira220_compat_ioctl32,
#endif
};

static const struct v4l2_subdev_video_ops mira220_video_ops = {
	.s_stream = mira220_s_stream,
	.g_frame_interval = mira220_g_frame_interval,
};

static const struct v4l2_subdev_pad_ops mira220_pad_ops = {
	.enum_mbus_code = mira220_enum_mbus_code,
	.enum_frame_size = mira220_enum_frame_sizes,
	.get_fmt = mira220_get_fmt,
	.set_fmt = mira220_set_fmt,
	.get_mbus_config = mira220_g_mbus_config,
};

static const struct v4l2_subdev_ops mira220_ops = {
	.core = &mira220_core_ops,
	.video = &mira220_video_ops,
	.pad = &mira220_pad_ops,
};

static const s64 mira220_link_freq_menu[] = { MIRA220_LINK_FREQ };

static int mira220_s_ctrl(struct v4l2_ctrl *ctrl)
{
	struct mira220 *m = container_of(ctrl->handler, struct mira220,
					 ctrl_handler);

	switch (ctrl->id) {
	case V4L2_CID_EXPOSURE:
		m->exp_reg = ctrl->val;
		return m->power_on ? mira220_write16(m, 0x100c, ctrl->val) : 0;
	case V4L2_CID_ANALOGUE_GAIN:
		/* Mira220 has no analog gain (AMS driver). Keep the V4L2
		 * control for 3A compatibility but never write 0x107d —
		 * that register is VSTART and a large value shears the frame.
		 */
		m->gain_reg = ctrl->val;
		return 0;
	default:
		return 0;
	}
}

static const struct v4l2_ctrl_ops mira220_ctrl_ops = {
	.s_ctrl = mira220_s_ctrl,
};

static int mira220_initialize_controls(struct mira220 *m)
{
	struct v4l2_ctrl_handler *h = &m->ctrl_handler;
	int ret;

	m->exp_reg = 4000;
	m->gain_reg = 256;
	ret = v4l2_ctrl_handler_init(h, 8);
	if (ret)
		return ret;
	v4l2_ctrl_new_int_menu(h, NULL, V4L2_CID_LINK_FREQ, 0, 0,
			       mira220_link_freq_menu);
	v4l2_ctrl_new_std(h, NULL, V4L2_CID_PIXEL_RATE, 0, MIRA220_PIXEL_RATE,
			  1, MIRA220_PIXEL_RATE);
	v4l2_ctrl_new_std(h, NULL, V4L2_CID_HBLANK, 0, 4096, 1, 400);
	v4l2_ctrl_new_std(h, NULL, V4L2_CID_VBLANK, 0, 4096, 1, 200);
	m->exposure = v4l2_ctrl_new_std(h, &mira220_ctrl_ops, V4L2_CID_EXPOSURE,
					1, 8000, 1, m->exp_reg);
	m->again = v4l2_ctrl_new_std(h, &mira220_ctrl_ops,
				     V4L2_CID_ANALOGUE_GAIN, 0, 1024, 1,
				     m->gain_reg);
	if (h->error)
		return h->error;
	m->subdev.ctrl_handler = h;
	return 0;
}

static int mira220_probe(struct i2c_client *client)
{
	struct device *dev = &client->dev;
	struct device_node *np = dev->of_node;
	struct mira220 *m;
	struct v4l2_subdev *sd;
	int ret, i;

	m = devm_kzalloc(dev, sizeof(*m), GFP_KERNEL);
	if (!m)
		return -ENOMEM;
	m->client = client;
	if (!np) {
		struct device_node *node;
		u32 reg = 0;

		for_each_compatible_node(node, NULL, "ams,mira220") {
			struct device_node *parent;
			const char *pn;

			if (of_property_read_u32(node, "reg", &reg))
				continue;
			if (reg != client->addr)
				continue;
			parent = of_get_parent(node);
			pn = parent ? of_node_full_name(parent) : "";
			if ((client->adapter->nr == 3 && strstr(pn, "21120000")) ||
			    (client->adapter->nr == 6 && strstr(pn, "i2c-gpio-cam1")) ||
			    (strstr(dev_name(dev), "3-0054") && strstr(pn, "21120000")) ||
			    (strstr(dev_name(dev), "6-0054") && strstr(pn, "i2c-gpio-cam1"))) {
				np = node;
				of_node_put(parent);
				break;
			}
			of_node_put(parent);
		}
	}
	m->module_index = (client->adapter && client->adapter->nr == 6) ? 1 : 0;
	m->module_facing = m->module_index ? "front" : "back";
	m->module_name = "camevision-mira220";
	m->len_name = "default";
	if (np) {
		u32 idx;
		const char *s;

		if (!of_property_read_u32(np, RKMODULE_CAMERA_MODULE_INDEX, &idx))
			m->module_index = idx;
		if (!of_property_read_string(np, RKMODULE_CAMERA_MODULE_FACING, &s))
			m->module_facing = s;
		if (!of_property_read_string(np, RKMODULE_CAMERA_MODULE_NAME, &s))
			m->module_name = s;
		if (!of_property_read_string(np, RKMODULE_CAMERA_LENS_NAME, &s))
			m->len_name = s;
	}
	if (np && !dev->of_node)
		dev->of_node = of_node_get(np);
	if (np) {
		struct pinctrl *pctl = devm_pinctrl_get_select_default(dev);

		if (IS_ERR(pctl))
			dev_warn(dev, "pinctrl default %ld\n", PTR_ERR(pctl));
	}
	m->xvclk = devm_clk_get(dev, "xvclk");
	if (IS_ERR(m->xvclk))
		m->xvclk = devm_clk_get(dev, "xclk");
	if (IS_ERR(m->xvclk) && np)
		m->xvclk = of_clk_get(np, 0);
	m->reset_gpio = devm_gpiod_get_optional(dev, "reset", GPIOD_OUT_HIGH);
	m->pwdn_gpio = devm_gpiod_get_optional(dev, "pwdn", GPIOD_OUT_HIGH);
	if (IS_ERR_OR_NULL(m->reset_gpio) && np)
		m->reset_gpio = fwnode_gpiod_get_index(of_fwnode_handle(np),
						      "reset", 0, GPIOD_OUT_HIGH,
						      "reset");
	dev_info(dev, "xvclk %s rate %lu reset %s pwdn %s\n",
		 IS_ERR(m->xvclk) ? "none" : "ok",
		 IS_ERR(m->xvclk) ? 0 : clk_get_rate(m->xvclk),
		 IS_ERR_OR_NULL(m->reset_gpio) ? "none" : "ok",
		 IS_ERR_OR_NULL(m->pwdn_gpio) ? "none" : "ok");
	for (i = 0; i < ARRAY_SIZE(mira220_supply_names); i++)
		m->supplies[i].supply = mira220_supply_names[i];
	ret = devm_regulator_bulk_get(dev, ARRAY_SIZE(m->supplies), m->supplies);
	if (ret)
		dev_warn(dev, "regulators optional (%d)\n", ret);

	m->fmt.width = MIRA220_W;
	m->fmt.height = MIRA220_H;
	m->fmt.code = MEDIA_BUS_FMT_SBGGR10_1X10;
	m->fmt.field = V4L2_FIELD_NONE;
	m->fmt.colorspace = V4L2_COLORSPACE_RAW;

	sd = &m->subdev;
	v4l2_i2c_subdev_init(sd, client, &mira220_ops);
	sd->flags |= V4L2_SUBDEV_FL_HAS_DEVNODE | V4L2_SUBDEV_FL_HAS_EVENTS;
	{
		const char *facing = "b";

		if (m->module_facing && m->module_facing[0] == 'f')
			facing = "f";
		snprintf(sd->name, sizeof(sd->name), "m%02d_%s_%s %s",
			 m->module_index, facing, MIRA220_NAME, dev_name(dev));
	}
	ret = mira220_initialize_controls(m);
	if (ret)
		goto err_ctrl;
	ret = mira220_power(m, true);
	if (ret)
		goto err_ctrl;
	pm_runtime_set_active(dev);
	pm_runtime_enable(dev);

	m->pad.flags = MEDIA_PAD_FL_SOURCE;
	sd->entity.function = MEDIA_ENT_F_CAM_SENSOR;
	ret = media_entity_pads_init(&sd->entity, 1, &m->pad);
	if (ret)
		goto err_power;
	ret = v4l2_async_register_subdev_sensor(sd);
	dev_info(dev, "async sensor register %d dev %s\n", ret, dev_name(dev));
	if (ret)
		ret = v4l2_async_register_subdev(sd);
	if (ret) {
		dev_err(dev, "async register %d\n", ret);
		goto err_entity;
	}
	if (!sd->devnode) {
		if (sd->v4l2_dev) {
			ret = v4l2_device_register_subdev_nodes(sd->v4l2_dev);
			dev_info(dev, "parent subdev nodes %d\n", ret);
		} else {
			ret = v4l2_device_register(dev, &m->v4l2_dev);
			if (!ret)
				ret = v4l2_device_register_subdev(&m->v4l2_dev, sd);
			if (!ret)
				ret = v4l2_device_register_subdev_nodes(&m->v4l2_dev);
			if (ret) {
				dev_err(dev, "own subdev node %d\n", ret);
				v4l2_device_unregister(&m->v4l2_dev);
				goto err_unreg;
			}
			m->own_v4l2 = true;
		}
	}
	dev_info(dev, "MIRA220 %s %s node %s\n", m->module_name, sd->name,
		 sd->devnode ? video_device_node_name(sd->devnode) : "none");
	return 0;

err_unreg:
	v4l2_async_unregister_subdev(sd);
err_entity:
	media_entity_cleanup(&sd->entity);
err_power:
	pm_runtime_disable(dev);
	mira220_power(m, false);
err_ctrl:
	v4l2_ctrl_handler_free(&m->ctrl_handler);
	return ret;
}

static void mira220_remove(struct i2c_client *client)
{
	struct v4l2_subdev *sd = i2c_get_clientdata(client);
	struct mira220 *m = to_mira220(sd);

	if (m->own_v4l2) {
		v4l2_device_unregister_subdev(sd);
		v4l2_device_unregister(&m->v4l2_dev);
	} else {
		v4l2_async_unregister_subdev(sd);
	}
	media_entity_cleanup(&sd->entity);
	v4l2_ctrl_handler_free(&m->ctrl_handler);
	pm_runtime_disable(&client->dev);
	mira220_power(m, false);
}

static const struct of_device_id mira220_of_match[] = {
	{ .compatible = "ams,mira220" },
	{ .compatible = "camevision,mira220" },
	{ }
};
MODULE_DEVICE_TABLE(of, mira220_of_match);

static struct i2c_driver mira220_i2c_driver = {
	.driver = {
		.name = MIRA220_NAME,
		.of_match_table = mira220_of_match,
	},
	.probe_new = mira220_probe,
	.remove = mira220_remove,
};

module_i2c_driver(mira220_i2c_driver);

MODULE_DESCRIPTION("AMS MIRA220 Rockchip sensor");
MODULE_LICENSE("GPL");
MODULE_VERSION("1.0");
