# -*- coding: utf-8 -*-
import asyncio
import json
from typing import Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from slugify import slugify


def slugify_did(host: str, mid_bind_id: str) -> str:
    """Slugify a device id."""
    return slugify(f'{host}_{mid_bind_id}', separator='_')


def slugify_name(name: str, separator: str = '_') -> str:
    """Slugify a name."""
    return slugify(name, separator=separator)


def get_service_name(type_: str) -> str:
    """Get service name from type."""
    service_strs: list[str] = type_.split(':')
    return service_strs[4]


def get_prop_name(type_: str) -> str:
    """Get property name from type."""
    prop_strs: list[str] = type_.split(':')
    return prop_strs[3]


def get_prop_endpoint(type_: str) -> str:
    """Get property endpoint from type."""
    prop_strs: list[str] = type_.split(':')
    return prop_strs[4]


def get_prop_group_key(product_identify: str, service_name: str, prop_name: str) -> str | None:
    """ 获取属性组key，同组属性需要一起发送 """
    if service_name == 'set_delay_switch' and prop_name in ['OnTime', 'OffWaitTime']:
        return f'{product_identify}_{service_name}'
    return None


class IoTHttp:
    """IoT Common HTTP API."""

    @staticmethod
    def get(url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> Optional[str]:
        full_url = url
        if params:
            encoded_params = urlencode(params)
            full_url = f'{url}?{encoded_params}'
        request = Request(full_url, method='GET', headers=headers or {})
        content: Optional[bytes] = None
        with urlopen(request) as response:
            content = response.read()
        return str(content, 'utf-8') if content else None

    @staticmethod
    def get_json(url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> Optional[dict]:
        response = IoTHttp.get(url, params, headers)
        return json.loads(response) if response else None

    @staticmethod
    async def get_json_async(
            url: str,
            params: Optional[dict] = None,
            headers: Optional[dict] = None,
            loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> Optional[dict]:
        ev_loop = loop or asyncio.get_running_loop()
        return await ev_loop.run_in_executor(None, IoTHttp.get_json, url, params, headers)
