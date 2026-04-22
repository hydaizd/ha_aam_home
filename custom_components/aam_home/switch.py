# -*- coding: utf-8 -*-
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .utils.iot_device import IoTPropertyEntity, IoTDevice
from .utils.iot_spec import IoTSpecProperty

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
        if iot_device.product_key in ["7504", "2668"]:
            _LOGGER.warning('------device2 product_key: %s', iot_device.product_key)
            spec: IoTSpecProperty = IoTSpecProperty(
                spec={
                    'name': f'{iot_device.endpoint} ',
                    'description': '',
                },
                value_list=[]
            )
            new_entities.append(AamSwitchEntity(iot_device=iot_device, spec=spec))

    if new_entities:
        _LOGGER.warning('调用 async_add_entities 添加实体')
        async_add_entities(new_entities)


class AamSwitchEntity(IoTPropertyEntity, SwitchEntity):
    """表示智空间盒子开关实体."""

    def __init__(self, iot_device: IoTDevice, spec: IoTSpecProperty) -> None:
        """初始化开关."""
        super().__init__(iot_device=iot_device, spec=spec)

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
