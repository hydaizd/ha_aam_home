# -*- coding: utf-8 -*-
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .utils.iot_device import IoTDevice, IoTActionEntity
from .utils.iot_spec import IoTSpecAction

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
        for action in iot_device.action_list.get('button', []):
            new_entities.append(AamButtonEntity(iot_device=iot_device, spec=action))
    
    if new_entities:
        async_add_entities(new_entities)


class AamButtonEntity(IoTActionEntity, ButtonEntity):
    """Button entities for Xiaomi Home."""

    def __init__(self, iot_device: IoTDevice, spec: IoTSpecAction) -> None:
        """Initialize the Button."""
        super().__init__(iot_device=iot_device, spec=spec)
        # Use default device class

    async def async_press(self) -> None:
        """Press the button."""
        return await self.action_async()
