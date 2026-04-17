# -*- coding: utf-8 -*-
import logging
from typing import Any

from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .utils.iot_device import IoTPropertyEntity, IoTDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """设置灯光平台."""
    device_list: list[IoTDevice] = hass.data[DOMAIN]['devices'][config_entry.entry_id]

    # 创建灯光实体
    new_entities = []
    for iot_device in device_list:
        if iot_device.product_key in ["7504"]:
            new_entities.append(AamLightEntity(iot_device=iot_device))

    if new_entities:
        async_add_entities(new_entities)


class AamLightEntity(IoTPropertyEntity, LightEntity):
    """表示智能盒子灯光实体."""

    def __init__(self, iot_device: IoTDevice) -> None:
        """初始化灯光."""
        super().__init__(iot_device=iot_device)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """打开灯光."""
        # 构建控制命令
        json_data = {"State": 1}

        # 处理亮度
        if "brightness" in kwargs:
            brightness = kwargs["brightness"]
            json_data["Brightness"] = brightness
            # self._attr_brightness = brightness

        # 处理颜色温度
        if "color_temp" in kwargs:
            color_temp = kwargs["color_temp"]
            json_data["ColorTemp"] = color_temp

        # 处理RGB颜色
        if "rgb_color" in kwargs:
            rgb_color = kwargs["rgb_color"]
            json_data["RGB"] = rgb_color

        cmd = ''
        await self.ctrl_device_async(self.iot_device, cmd, json_data)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭灯光."""
        cmd = ''
        json_data = {"State": 0}
        await self.ctrl_device_async(self.iot_device, cmd, json_data)
