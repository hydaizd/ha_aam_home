# -*- coding: utf-8 -*-
import asyncio
from typing import Any, Optional

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity import Entity

from .common import slugify_did, slugify_name
from .iot_client import IoTClient, IoTClientError
from .iot_error import IoTDeviceError
from .iot_spec import IoTSpecValueList, IoTSpecProperty, IoTSpecAction
from ..const import DOMAIN


class IoTDevice:
    """智能设备."""
    # pylint: disable=unused-argument
    iot_client: IoTClient

    _online: bool

    _mid_bind_id: str
    _name: str
    _model: str
    _manufacturer: str
    _fw_version: str
    _product_key: str
    _endpoint: str
    _group_id: str
    _endpoint_name: str

    def __init__(self, iot_client: IoTClient, device_info: dict[str, Any]) -> None:
        self.iot_client = iot_client

        # 当设备不在线时会显示不可用
        self._online = device_info.get('onlineStatus', 0) == 1
        self._mid_bind_id = device_info.get('midBindId', '')
        self._name = device_info.get('name', '')
        self._product_key = device_info.get('productKey', '')
        self._group_id = device_info.get('groupId', '')
        self._endpoint = device_info.get('endpoint', '')
        self._endpoint_name = device_info.get('endpointName', '')

        self._model = device_info.get('skuId', '')
        self._manufacturer = device_info.get('manufacturer', '艾美科技')
        self._fw_version = device_info.get('version', '')

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

    @property
    def model(self) -> str:
        return self._model

    @property
    def did_tag(self) -> str:
        return slugify_did(host=self.iot_client.host, mid_bind_id=self._mid_bind_id)

    @property
    def device_info(self) -> DeviceInfo:
        """设备信息."""
        return DeviceInfo(
            # 设备唯一标识
            identifiers={(DOMAIN, self.did_tag)},
            name=self._name,
            sw_version=self._fw_version,
            model=self._model,
            manufacturer=self._manufacturer,
            # suggested_area=self._suggested_area,
            # configuration_url=('')
        )

    def gen_prop_entity_id(self, ha_domain: str, spec_name: str, mid_bind_id: str, endpoint: str) -> str:
        return f'{ha_domain}.{slugify_name(spec_name)}_{mid_bind_id}_{endpoint}'

    def gen_action_entity_id(self, ha_domain: str, spec_name: str, mid_bind_id: str, endpoint: str) -> str:
        return f'{ha_domain}.{slugify_name(spec_name)}_{mid_bind_id}_{endpoint}'


class IoTPropertyEntity(Entity):
    """智能设备属性."""
    iot_device: IoTDevice
    spec: IoTSpecProperty
    _main_loop: asyncio.AbstractEventLoop
    _value_list: Optional[IoTSpecValueList]
    _value: Any

    def __init__(self, iot_device: IoTDevice, spec: IoTSpecProperty) -> None:
        self.iot_device = iot_device
        self.spec = spec
        self._value_list = spec.value_list
        self._value = None
        self.entity_id = self.iot_device.gen_prop_entity_id(
            ha_domain=DOMAIN,
            spec_name=spec.name,
            mid_bind_id=iot_device.mid_bind_id,
            endpoint=iot_device.endpoint
        )
        # Set entity attr
        self._attr_unique_id = self.entity_id  # 实体唯一标识
        self._attr_should_poll = False
        self._attr_has_entity_name = True  # 是否有实体名称
        self._attr_name = f'{iot_device.endpoint_name}  {spec.description}'  # 实体名
        self._attr_available = iot_device.online  # 实体当前是否可用

    @property
    def device_info(self) -> Optional[DeviceInfo]:
        return self.iot_device.device_info

    def get_vlist_description(self, value: Any) -> Optional[str]:
        # 根据值获取描述
        if not self._value_list:
            return None
        return self._value_list.get_description_by_value(value)

    def get_vlist_value(self, description: str) -> Any:
        # 根据描述获取值
        if not self._value_list:
            return None
        return self._value_list.get_value_by_description(description)

    async def ctrl_device_async(self, cmd: str, value: any, json_data: dict) -> bool:
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
        self._value = value
        # 立即更新UI
        self.async_write_ha_state()
        return True


class IoTActionEntity(Entity):
    """智能设备操作."""
    iot_device: IoTDevice
    spec: IoTSpecAction
    _main_loop: asyncio.AbstractEventLoop
    _value_list: Optional[IoTSpecValueList]
    _value: Any

    def __init__(self, iot_device: IoTDevice, spec: IoTSpecAction) -> None:
        if iot_device is None or spec is None:
            raise IoTDeviceError('init error, invalid params')
        self.iot_device = iot_device
        self.spec = spec
        self._main_loop = iot_device.iot_client.main_loop
        # Gen entity_id
        self.entity_id = self.iot_device.gen_action_entity_id(
            ha_domain=DOMAIN,
            spec_name=spec.name,
            mid_bind_id=iot_device.mid_bind_id,
            endpoint=iot_device.endpoint
        )
        # Set entity attr
        self._attr_unique_id = self.entity_id
        self._attr_should_poll = False
        self._attr_has_entity_name = True
        self._attr_name = f'{iot_device.endpoint_name}  {spec.description}'  # 实体名
        self._attr_available = iot_device.online

    @property
    def device_info(self) -> Optional[DeviceInfo]:
        return self.iot_device.device_info
