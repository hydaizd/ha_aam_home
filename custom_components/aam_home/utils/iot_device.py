# -*- coding: utf-8 -*-
from typing import Any

from homeassistant.helpers.entity import Entity

from .iot_client import IoTClient, IoTClientError


class IoTDevice:
    """智能设备."""
    # pylint: disable=unused-argument
    iot_client: IoTClient

    _online: bool

    _mid_bind_id: str
    _name: str
    _product_key: str
    _endpoint: str
    _group_id: str

    def __init__(self, iot_client: IoTClient, device_info: dict[str, Any]) -> None:
        self.iot_client = iot_client

        self._online = device_info.get('onlineStatus', 0) == 1
        self._mid_bind_id = device_info.get('midBindId', '')
        self._name = device_info.get('name', '')
        self._product_key = device_info.get('productKey', '')
        self._endpoint = device_info.get('endpoint', '')

    @property
    def online(self) -> bool:
        return self._online

    @property
    def mid_bind_id(self) -> str:
        return self._mid_bind_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def product_key(self) -> str:
        return self._product_key

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def group_id(self) -> str:
        return self._group_id


class IoTPropertyEntity(Entity):
    """智能设备属性."""
    iot_device: IoTDevice
    _value: dict

    def __init__(self, iot_device: IoTDevice) -> None:
        self.iot_device = iot_device

    async def ctrl_device_async(self, cmd: str, json_data: dict) -> bool:
        try:
            await self.iot_device.iot_client.ctrl_device_async(
                cmd=cmd,
                mid_bind_id=self.iot_device.mid_bind_id,
                endpoint=self.iot_device.endpoint,
                group_id=self.iot_device.group_id,
                json_data=json_data,
            )
        except IoTClientError as e:
            raise RuntimeError(f'{e}, {self.iot_device.mid_bind_id}, {self.iot_device.name}') from e
        self._value = json_data
        self.async_write_ha_state()
        return True
