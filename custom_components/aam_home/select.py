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
        if iot_device.product_key in ["2668"]:
            spec: IoTSpecProperty = IoTSpecProperty(
                spec={
                    'name': f'select_{iot_device.endpoint} ',
                    'description': '默认上电状态',
                },
                value_list=[
                    {
                        'name': 'EpWorkMode1',
                        'value': 64,
                        'description': '通电打开',
                    },
                    {
                        'name': 'EpWorkMode2',
                        'value': 96,
                        'description': '通电关闭',
                    },
                    {
                        'name': 'EpWorkMode3',
                        'value': 160,
                        'description': '保持断电前状态',
                    }
                ],
            )
            new_entities.append(AamSelectEntity(iot_device=iot_device, spec=spec))

    if new_entities:
        async_add_entities(new_entities)


class AamSelectEntity(IoTPropertyEntity, SelectEntity):
    def __init__(self, iot_device: IoTDevice, spec: IoTSpecProperty) -> None:
        """Initialize the Select."""
        super().__init__(iot_device=iot_device, spec=spec)
        if self._value_list:
            self._attr_options = self._value_list.descriptions

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        cmd = "aam_socket_ep_workmode"
        json_data = {"EpWorkMode": self.get_vlist_value(description=option)}
        await self.ctrl_device_async(cmd, json_data)

    @property
    def current_option(self) -> Optional[str]:
        """Return the current selected option."""
        return self.get_vlist_description(value=self._value)
