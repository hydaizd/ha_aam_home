# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import Any, Union, Optional

from .http_client import IoTHttpClient
from .iot_error import IoTSpecError

_LOGGER = logging.getLogger(__name__)


class IoTSpecValueRange:
    """IoT SPEC value range class."""
    min_: int
    max_: int
    step: int | float

    def __init__(self, value_range: Union[dict, list]) -> None:
        if isinstance(value_range, dict):
            self.load(value_range)
        elif isinstance(value_range, list):
            self.from_spec(value_range)
        else:
            raise IoTSpecError('invalid value range format')

    def load(self, value_range: dict) -> None:
        if 'min' not in value_range or 'max' not in value_range or 'step' not in value_range:
            raise IoTSpecError('invalid value range')
        self.min_ = value_range['min']
        self.max_ = value_range['max']
        self.step = value_range['step']

    def from_spec(self, value_range: list) -> None:
        if len(value_range) != 3:
            raise IoTSpecError('invalid value range')
        self.min_ = value_range[0]
        self.max_ = value_range[1]
        self.step = value_range[2]

    def dump(self) -> dict:
        return {'min': self.min_, 'max': self.max_, 'step': self.step}

    def __str__(self) -> str:
        return f'[{self.min_}, {self.max_}, {self.step}'


class IoTSpecValueListItem:
    """IoT 规范值列表项类."""
    # NOTICE: bool type without name
    name: str
    # Value
    value: Any
    # Descriptions after multilingual conversion.
    description: str

    def __init__(self, item: dict) -> None:
        self.load(item)

    def load(self, item: dict) -> None:
        if 'value' not in item or 'description' not in item:
            raise IoTSpecError('invalid value list item, %s')

        self.name = item.get('name', None)
        self.value = item['value']
        self.description = item['description']


class IoTSpecValueList:
    """IoT 规范值列表类."""
    # pylint: disable=inconsistent-quotes
    items: list[IoTSpecValueListItem]

    def __init__(self, value_list: list[dict]) -> None:
        if not isinstance(value_list, list):
            raise IoTSpecError('invalid value list format')
        self.items = []
        self.load(value_list)

    @property
    def descriptions(self) -> list[str]:
        return [item.description for item in self.items]

    def load(self, value_list: list[dict]) -> None:
        for item in value_list:
            self.items.append(IoTSpecValueListItem(item))

    def get_value_by_description(self, description: str) -> Any:
        for item in self.items:
            if item.description == description:
                return item.value
        return None

    def get_description_by_value(self, value: Any) -> str | None:
        for item in self.items:
            if item.value == value:
                return item.description
        return None


class _IoTSpecBase:
    """IoT 规范基类."""
    type_: str
    description: str
    name: str

    platform: str | None

    def __init__(self, spec: dict) -> None:
        self.type_ = spec['type']
        self.description = spec['description']
        self.name = spec.get('name', 'aam')

        self.platform = None


class IoTSpecProperty(_IoTSpecBase):
    """IoT 规范属性类."""
    unit: Optional[str]
    _format_: type
    _value_range: IoTSpecValueRange | None
    _value_list: IoTSpecValueList | None

    service: 'IoTSpecService'

    def __init__(
            self,
            spec: dict,
            service: 'IoTSpecService',
            format_: str,
            unit: Optional[str] = None,
            value_range: Optional[dict] = None,
            value_list: Optional[list[dict]] = None,
    ) -> None:
        super().__init__(spec=spec)
        self.service = service
        self.format_ = format_
        self.unit = unit
        self.value_range = value_range
        self.value_list = value_list

    @property
    def format_(self) -> type:
        return self._format_

    @format_.setter
    def format_(self, value: str) -> None:
        self._format_ = {
            'string': str,
            'str': str,
            'bool': bool,
            'float': float
        }.get(value, int)

    @property
    def value_range(self) -> IoTSpecValueRange | None:
        return self._value_range

    @value_range.setter
    def value_range(self, value: dict | list | None) -> None:
        """Set value-range, precision."""
        if not value:
            self._value_range = None
            return
        self._value_range = IoTSpecValueRange(value_range=value)

    @property
    def value_list(self) -> IoTSpecValueList | None:
        return self._value_list

    @value_list.setter
    def value_list(self, value: list[dict] | IoTSpecValueList | None) -> None:
        if not value:
            self._value_list = None
            return
        if isinstance(value, list):
            self._value_list = IoTSpecValueList(value_list=value)
        elif isinstance(value, IoTSpecValueList):
            self._value_list = value

    def __str__(self) -> str:
        return (
            f'IoTSpecProperty(name={self.name}, '
            f'type={self.type_}, '
            f'description={self.description}, '
            f'unit={self.unit}, '
            f'format={self.format_}, '
            f'value_range={self.value_range}, '
            f'value_list={self.value_list})'
        )


class IoTSpecEvent(_IoTSpecBase):
    """IoT 规范事件类."""
    argument: list[IoTSpecProperty]

    def __init__(
            self,
            spec: dict,
            argument: list[IoTSpecProperty] | None = None) -> None:
        super().__init__(spec=spec)
        self.argument = argument or []


class IoTSpecAction(_IoTSpecBase):
    """IoT 规范操作类."""
    in_: list[IoTSpecProperty]
    out: list[IoTSpecProperty]

    def __init__(
            self,
            spec: dict,
            in_: list[IoTSpecProperty] | None = None,
            out: list[IoTSpecProperty] | None = None
    ) -> None:
        super().__init__(spec=spec)
        self.in_ = in_ or []
        self.out = out or []


class IoTSpecService(_IoTSpecBase):
    """IoT 规范服务类."""

    def __init__(self, spec: dict) -> None:
        super().__init__(spec=spec)


class IoTSpecInstance:
    """IoT 规范实例类."""
    product_identify: str  # 产品唯一标识(产品key或sku_id)
    name: str
    description: str
    description_trans: str

    properties: list[IoTSpecProperty]
    events: list[IoTSpecEvent]
    actions: list[IoTSpecAction]

    def __init__(self, product_identify: str, name: str, description: str, description_trans: str) -> None:
        self.product_identify = product_identify
        self.name = name
        self.description = description
        self.description_trans = description_trans

        self.properties = []
        self.events = []
        self.actions = []

    def __str__(self) -> str:
        return (
            f'IoTSpecInstance(product_identify={self.product_identify}, '
            f'name={self.name}, '
            f'description={self.description}, '
            f'description_trans={self.description_trans}, '
            f'properties={len(self.properties)}, '
            f'events={len(self.events)}, '
            f'actions={len(self.actions)})'
        )


class IoTSpecParser:
    """IoT 规范解析器."""
    _main_loop: asyncio.AbstractEventLoop
    # IoT http client
    _http: IoTHttpClient | None

    def __init__(
            self,
            iot_http: IoTHttpClient | None = None,
            loop: asyncio.AbstractEventLoop | None = None
    ) -> None:
        self._main_loop = loop or asyncio.get_running_loop()
        self._http = iot_http

    async def __get_instance(self, product_key: str, sku_id: str) -> dict | None:
        """获取产品实例."""
        return await self._http.get_device_instance_async(product_key=product_key, sku_id=sku_id)

    async def parse(self, product_key: str, sku_id: str) -> IoTSpecInstance | None:
        # 过滤掉product_key 和 sku_id 同时为空的设备
        if not product_key and not sku_id:
            return None

        # 指定产品测试
        if product_key != '2668':
            return None

        # 重试3次
        for index in range(3):
            try:
                return await self.__parse(product_key=product_key, sku_id=sku_id)
            except Exception as err:
                _LOGGER.error('parse error, retry, %d, product_key: %s, sku_id: %s, %s', index, product_key, sku_id,
                              err)
        return None

    async def __parse(self, product_key: str, sku_id: str) -> IoTSpecInstance:
        _LOGGER.debug('parse product, %s, %s', product_key, sku_id)

        # Load spec instance
        instance = await self.__get_instance(product_key=product_key, sku_id=sku_id)
        if not isinstance(instance, dict):
            raise IoTSpecError(f'invalid product instance, {product_key}, {sku_id}')

        product_identify = sku_id
        # 优先使用product_key
        if product_key:
            product_identify = product_key

        # Parse device type
        spec_instance: IoTSpecInstance = IoTSpecInstance(
            product_identify=product_identify,
            name="hhhhhhhhhh",
            description='bbbbbbbbbbbbbbbb',
            description_trans="tesdfdfjpafjafjpafja"
        )

        urn_service_instance = instance.get('services', [])

        # Parse services
        for service in urn_service_instance:
            if 'type' not in service or 'description' not in service:
                _LOGGER.error('invalid service, %s', service)
                continue

            type_strs: list[str] = service['type'].split(':')
            spec_service: IoTSpecService = IoTSpecService(spec=service)
            spec_service.name = type_strs[4]

            for property_ in service.get('properties', []):
                if 'type' not in property_ or 'description' not in property_ or 'format' not in property_:
                    continue
                property_['description'] = f'{service['description']} | {property_['description']}'
                p_type_strs: list[str] = property_['type'].split(':')
                unit = property_.get('unit', None)
                spec_prop: IoTSpecProperty = IoTSpecProperty(
                    spec=property_,
                    service=spec_service,
                    format_=property_['format'],
                    unit=unit if unit != 'none' else None
                )
                spec_prop.name = p_type_strs[3]
                # 为None时则根据format判断平台类型
                spec_prop.platform = self._get_platform(property_)

                if 'value-list' in property_:
                    spec_prop.value_list = property_['value-list']
                if 'value-range' in property_:
                    spec_prop.value_range = property_['value-range']

                spec_instance.properties.append(spec_prop)
        return spec_instance

    def _get_platform(self, property_: dict) -> str | None:
        """ 获取ha平台类型，取值只有0和1的属性转化为switch布尔型 """
        if property_['format'] in ['enum', 'int_enum'] and 'value-list' in property_ and len(
                property_['value-list']) == 2:
            values = []
            for value_info in property_['value-list']:
                values.append(value_info['value'])
            sort_values = sorted(values)
            if sort_values == [0, 1] or sort_values == ['0', '1']:
                return 'switch'
        return None
