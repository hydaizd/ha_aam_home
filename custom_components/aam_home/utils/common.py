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
