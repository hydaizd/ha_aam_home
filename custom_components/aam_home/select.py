# -*- coding: utf-8 -*-
import logging
from typing import Optional

from homeassistant.components.select import SelectEntity
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
    """Set up a config entry."""
    device_list: list[IoTDevice] = hass.data[DOMAIN]['devices'][config_entry.entry_id]

    new_entities = []
    for iot_device in device_list:
        for prop in iot_device.prop_list.get('select', []):
            new_entities.append(AamSelectEntity(iot_device=iot_device, spec=prop))

    if new_entities:
        async_add_entities(new_entities)


class AamSelectEntity(IoTPropertyEntity, SelectEntity):
    def __init__(self, iot_device: IoTDevice, spec: IoTSpecProperty) -> None:
        """Initialize the Select."""
        super().__init__(iot_device=iot_device, spec=spec)
        if self._value_list:
            # 下拉框所有选项
            self._attr_options = self._value_list.descriptions

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        value = self.get_vlist_value(description=option)
        await self.set_property_async(value)

    @property
    def current_option(self) -> Optional[str]:
        """Return the current selected option."""
        return self.get_vlist_description(value=self._value)
