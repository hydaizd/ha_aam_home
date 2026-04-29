# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity import Entity

from .common import slugify_did, slugify_name, get_service_name, get_prop_name, get_prop_endpoint
from .iot_client import IoTClient, IoTClientError
from .iot_error import IoTDeviceError
from .iot_spec import IoTSpecValueList, IoTSpecProperty, IoTSpecAction, IoTSpecInstance, IoTSpecEvent, IoTSpecValueRange
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class IoTEntityData:
    """IoT 实体数据."""
    platform: str
    spec: IoTSpecInstance

    def __init__(self, platform: str, spec: IoTSpecInstance) -> None:
        self.platform = platform
        self.spec = spec


class IoTDevice:
    """智能设备."""
    # pylint: disable=unused-argument
    iot_client: IoTClient
    spec_instance: IoTSpecInstance

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

    _entity_list: dict[str, list[IoTEntityData]]
    _prop_list: dict[str, list[IoTSpecProperty]]
    _event_list: dict[str, list[IoTSpecEvent]]
    _action_list: dict[str, list[IoTSpecAction]]

    def __init__(self, iot_client: IoTClient, device_info: dict[str, Any], spec_instance: IoTSpecInstance) -> None:
        self.iot_client = iot_client
        self.spec_instance = spec_instance
        self._entity_map = {}

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

        self._entity_list = {}
        self._prop_list = {}
        self._event_list = {}
        self._action_list = {}

    @property
    def entity_list(self) -> dict[str, list[IoTEntityData]]:
        return self._entity_list

    @property
    def prop_list(self) -> dict[str, list[IoTSpecProperty]]:
        return self._prop_list

    @property
    def event_list(self) -> dict[str, list[IoTSpecEvent]]:
        return self._event_list

    @property
    def action_list(self) -> dict[str, list[IoTSpecAction]]:
        return self._action_list

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

    def append_entity(self, entity_data: IoTEntityData) -> None:
        self._entity_list.setdefault(entity_data.platform, [])
        self._entity_list[entity_data.platform].append(entity_data)

    def append_prop(self, prop: IoTSpecProperty) -> None:
        if not prop.platform:
            return
        self._prop_list.setdefault(prop.platform, [])
        self._prop_list[prop.platform].append(prop)

    def append_event(self, event: IoTSpecEvent) -> None:
        if not event.platform:
            return
        self._event_list.setdefault(event.platform, [])
        self._event_list[event.platform].append(event)

    def append_action(self, action: IoTSpecAction) -> None:
        if not action.platform:
            return
        self._action_list.setdefault(action.platform, [])
        self._action_list[action.platform].append(action)

    def spec_transform(self) -> None:
        """解析属性、事件、操作规范."""
        # device_entity = self.parse_miot_device_entity(spec_instance=self.spec_instance)
        # if device_entity:
        #     self.append_entity(entity_data=device_entity)

        for prop in self.spec_instance.properties:
            # 过滤掉不支持该属性的endpoint
            if self.endpoint != get_prop_endpoint(prop.type_):
                continue

            if not prop.platform:
                if prop.format_ == str:
                    prop.platform = 'text'
                elif prop.format_ == bool:
                    prop.platform = 'switch'
                elif prop.value_list:
                    prop.platform = 'select'
                elif prop.value_range:
                    prop.platform = 'number'
                else:
                    # Irregular property will not be transformed.
                    continue
            self.append_prop(prop=prop)
        for event in self.spec_instance.events:
            if event.platform:
                continue
            event.platform = 'event'
            self.append_event(event=event)
        for action in self.spec_instance.actions:
            if action.platform:
                continue
            if action.in_:
                action.platform = 'notify'
            else:
                action.platform = 'button'
            self.append_action(action=action)


class IoTPropertyEntity(Entity):
    """智能设备属性."""
    hass: HomeAssistant
    iot_device: IoTDevice
    spec: IoTSpecProperty
    _main_loop: asyncio.AbstractEventLoop
    _value_range: Optional[IoTSpecValueRange]
    _value_list: Optional[IoTSpecValueList]
    _value: Any

    _cmd: str  # 修改属性的命令
    _param_key: str  # 修改属性的参数key

    def __init__(self, hass: HomeAssistant, iot_device: IoTDevice, spec: IoTSpecProperty) -> None:
        self.hass = hass
        self.iot_device = iot_device
        self.spec = spec
        self._value_range = spec.value_range
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

        # 解析属性设置命令和参数
        self._cmd = get_service_name(spec.service.type_)
        self._param_key = get_prop_name(spec.type_)

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

    async def set_property_async(self, value: any) -> bool:
        try:
            json_data = {self._param_key: value}

            # 如果属性有group_key，需要收集同一组的其他属性一起发送
            if self.spec.group_key:
                entity_reg = entity_registry.async_get(self.hass)
                # 获取设备的所有实体
                entities = entity_registry.async_entries_for_device(entity_reg, self.iot_device.mid_bind_id)
                for entity in entities:
                    _LOGGER.warning(f'entity: {entity}')
                    if entity.group_key == self.spec.group_key and entity.name != self.spec.name:
                        # 获取同一组其他属性的当前值
                        json_data[entity.name] = entity._value
                        break

            await self.iot_device.iot_client.set_prop_async(
                cmd=self._cmd,
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

    async def action_async(self, in_list: Optional[list] = None) -> Optional[list]:
        _LOGGER.warning(f'action_async, {self.entity_id}, {in_list}')
        return None
