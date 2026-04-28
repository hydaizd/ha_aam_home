# -*- coding: utf-8 -*-

from typing import Optional

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .utils.iot_device import IoTPropertyEntity, IoTDevice
from .utils.iot_spec import IoTSpecProperty


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    device_list: list[IoTDevice] = hass.data[DOMAIN]['devices'][config_entry.entry_id]

    new_entities = []
    for iot_device in device_list:
        for prop in iot_device.prop_list.get('number', []):
            new_entities.append(AamNumberEntity(iot_device=iot_device, spec=prop))

    if new_entities:
        async_add_entities(new_entities)


class AamNumberEntity(IoTPropertyEntity, NumberEntity):
    def __init__(self, iot_device: IoTDevice, spec: IoTSpecProperty) -> None:
        super().__init__(iot_device=iot_device, spec=spec)

        # Set value range
        if self._value_range:
            self._attr_native_min_value = self._value_range.min_
            self._attr_native_max_value = self._value_range.max_
            self._attr_native_step = self._value_range.step

    @property
    def native_value(self) -> Optional[float]:
        """Return the current value of the number."""
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        # await self.set_property_async(value=value)
