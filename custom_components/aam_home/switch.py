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
        for prop in iot_device.prop_list.get('switch', []):
            new_entities.append(AamSwitchEntity(iot_device=iot_device, spec=prop))

    if new_entities:
        async_add_entities(new_entities)


class AamSwitchEntity(IoTPropertyEntity, SwitchEntity):
    """表示智空间盒子开关实体."""

    def __init__(self, iot_device: IoTDevice, spec: IoTSpecProperty) -> None:
        """初始化开关."""
        super().__init__(iot_device=iot_device, spec=spec)

    @property
    def is_on(self) -> bool:
        """开/关 状态."""
        return self._value == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """打开开关."""
        value = 1
        await self.ctrl_device_async("set_state", value, {"State": value})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭开关."""
        value = 0
        await self.ctrl_device_async("set_state", value, {"State": value})

    async def async_toggle(self, **kwargs: Any) -> None:
        """切换开关."""
        value = 0 if self.is_on else 1
        await self.ctrl_device_async("set_state", value, {"State": value})
