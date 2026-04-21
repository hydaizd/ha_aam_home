# -*- coding: utf-8 -*-
from typing import Any, Optional

from .iot_error import IoTSpecError


class IoTSpecValueListItem:
    """MIoT SPEC value list item class."""
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
    """IoT规范值列表类."""
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


class _IoTSpecBase:
    """IoT 规范基类."""
    description: str
    name: str

    def __init__(self, spec: dict) -> None:
        self.description = spec['description']
        self.name = spec.get('name', 'aam')


class IoTSpecProperty(_IoTSpecBase):
    """IoT 规范属性类."""
    _value_list: Optional[IoTSpecValueList]

    def __init__(self, spec: dict, value_list: Optional[list[dict]] = None) -> None:
        super().__init__(spec=spec)
        self.value_list = value_list
