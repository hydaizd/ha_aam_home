# -*- coding: utf-8 -*-
import asyncio
from typing import Any, Optional

from homeassistant.helpers.entity import Entity

from .iot_client import IoTClient, IoTClientError
from ..const import DOMAIN


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
    _endpoint_name: str

    def __init__(self, iot_client: IoTClient, device_info: dict[str, Any]) -> None:
        self.iot_client = iot_client

        self._online = device_info.get('onlineStatus', 0) == 1
        self._mid_bind_id = device_info.get('midBindId', '')
        self._name = device_info.get('name', '')
        self._product_key = device_info.get('productKey', '')
        self._group_id = device_info.get('groupId', '')
        self._endpoint = device_info.get('endpoint', '')
        self._endpoint_name = device_info.get('endpointName', '')

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

    @property
    def endpoint_name(self) -> str:
        return self._endpoint_name

    def gen_prop_entity_id(self, ha_domain: str, mid_bind_id: str, endpoint: str) -> str:
        return f'{ha_domain}.{mid_bind_id}_{endpoint}'


class IoTPropertyEntity(Entity):
    """智能设备属性."""
    iot_device: IoTDevice
    _main_loop: asyncio.AbstractEventLoop
    _value: Optional[dict]

    def __init__(self, iot_device: IoTDevice) -> None:
        self.iot_device = iot_device
        self._value = None
        self.entity_id = self.iot_device.gen_prop_entity_id(ha_domain=DOMAIN, mid_bind_id=iot_device.mid_bind_id,
                                                            endpoint=iot_device.endpoint)
        # Set entity attr
        self._attr_unique_id = self.entity_id  # 实体唯一标识
        self._attr_should_poll = False
        self._attr_has_entity_name = True  # 是否有实体名称
        self._attr_name = iot_device.endpoint_name or f"开关 {iot_device.endpoint}"  # 实体名
        self._attr_available = iot_device.online  # 实体当前是否可用

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
