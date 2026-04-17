# -*- coding: utf-8 -*-
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .utils.iot_device import IoTPropertyEntity, IoTDevice

# 用于在 HA 前端显示的名称
DEFAULT_NAME = "Aam Home Controlled Switch"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """设置开关平台."""
    device_list: list[IoTDevice] = hass.data[DOMAIN]['devices'][config_entry.entry_id]

    # 创建开关实体
    new_entities = []
    for iot_device in device_list:
        _LOGGER.warning('device product_key: %s', iot_device.product_key)
        if iot_device.product_key in ["7504"]:
            _LOGGER.warning('------device2 product_key: %s', iot_device.product_key)
            new_entities.append(AamSwitchEntity(iot_device=iot_device))

    if new_entities:
        _LOGGER.warning('调用 async_add_entities 添加实体')
        async_add_entities(new_entities)


class AamSwitchEntity(IoTPropertyEntity, SwitchEntity):
    """表示智空间盒子开关实体."""

    def __init__(self, iot_device: IoTDevice) -> None:
        """初始化开关."""
        super().__init__(iot_device=iot_device)

        # 设备属性
        self._attr_name = iot_device.endpoint_name or f"开关 {iot_device.endpoint}"  # 实体名
        self._attr_unique_id = f"{iot_device.mid_bind_id}_{iot_device.endpoint}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, iot_device.mid_bind_id)},
            "name": iot_device.name,  # 设备名
            "manufacturer": "艾美科技",
        }

    @property
    def is_on(self) -> bool:
        """开/关 状态."""
        if self._value is None:
            return False
        return self._value.get("State", 0) == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """打开开关."""
        cmd = "set_state"
        json_data = {"State": 1}
        await self.ctrl_device_async(cmd, json_data)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭开关."""
        cmd = "set_state"
        json_data = {"State": 0}
        await self.ctrl_device_async(cmd, json_data)

    async def async_toggle(self, **kwargs: Any) -> None:
        """切换开关."""
        cmd = "set_state"
        if self.is_on:
            json_data = {"State": 0}
        else:
            json_data = {"State": 1}
        await self.ctrl_device_async(cmd, json_data)
