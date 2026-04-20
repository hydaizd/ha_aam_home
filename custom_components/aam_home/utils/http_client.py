# -*- coding: utf-8 -*-
import asyncio
import hashlib
import json
import logging
from typing import Optional

import aiohttp

from .iot_error import IoTHttpError, IoTErrorCode, IoTAuthError
from ..const import HTTP_API_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class IoTAuthClient:
    """IoT auth client."""
    _main_loop: asyncio.AbstractEventLoop
    _session: aiohttp.ClientSession
    _host: str
    _username: str
    _password: str

    def __init__(
            self,
            host: str,
            username: str,
            password: str,
            loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        self._host = host
        self._username = username
        self._password = password
        self._main_loop = loop or asyncio.get_running_loop()
        self._session = aiohttp.ClientSession()

    async def de_init_async(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_access_token_async(self) -> dict:
        """Get access token."""
        md5 = hashlib.md5()
        md5.update(self._password.encode())

        payload = {
            "username": self._username,
            "passwd": md5.hexdigest()
        }
        http_res = await self._session.post(
            url=f'http://{self._host}:10088/api/basic/user/login',
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=HTTP_API_TIMEOUT
        )
        if http_res.status != 200:
            raise IoTAuthError(f'invalid http status code, {http_res.status}')

        res_str = await http_res.text()
        res_obj: dict = json.loads(res_str)
        if not res_obj.get("success"):
            raise IoTAuthError(f'invalid http response, {res_obj.get("msg")}')

        # 登录成功
        return {
            'access_token': res_obj.get("data")
        }


class IoTHttpClient:
    """IoT http client."""
    # pylint: disable=inconsistent-quotes
    _main_loop: asyncio.AbstractEventLoop
    _session: aiohttp.ClientSession
    _host: str
    _base_url: str
    _access_token: str

    def __init__(self, host: str, access_token: str, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self._main_loop = loop or asyncio.get_running_loop()
        self._host = host
        self._base_url = f'http://{host}:10088'
        self._access_token = ''

        self.update_http_header(access_token=access_token)

        self._session = aiohttp.ClientSession()

    async def de_init_async(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def update_http_header(self, access_token: Optional[str] = None) -> None:
        if isinstance(access_token, str):
            self._access_token = access_token

    @property
    def __api_request_headers(self) -> dict:
        return {
            'Content-Type': 'application/json',
            'Authorization': f'{self._access_token}',
        }

    # pylint: disable=unused-private-member
    async def __api_get_async(self, url_path: str, params: dict, timeout: int = HTTP_API_TIMEOUT) -> dict:
        """Get方式请求api."""
        http_res = await self._session.get(
            url=f'{self._base_url}{url_path}',
            params=params,
            headers=self.__api_request_headers,
            timeout=timeout)
        if http_res.status == 401:
            raise IoTHttpError('api get failed, unauthorized(401)', IoTErrorCode.CODE_HTTP_INVALID_ACCESS_TOKEN)
        if http_res.status != 200:
            raise IoTHttpError(f'api get failed, {http_res.status}, 'f'{url_path}, {params}')

        res_str = await http_res.text()
        res_obj: dict = json.loads(res_str)
        if not res_obj.get('success', None):
            raise IoTHttpError(f'invalid response, {res_obj.get("success", None)}, 'f'{res_obj.get("msg", "")}')
        _LOGGER.debug('api get, %s%s, %s -> %s', self._base_url, url_path, params, res_obj)
        return res_obj

    async def __api_post_async(self, url_path: str, data: dict, timeout: int = HTTP_API_TIMEOUT) -> dict:
        """Post方式请求api."""
        http_res = await self._session.post(
            url=f'{self._base_url}{url_path}',
            json=data,
            headers=self.__api_request_headers,
            timeout=timeout)
        if http_res.status == 401:
            raise IoTHttpError('api get failed, unauthorized(401)', IoTErrorCode.CODE_HTTP_INVALID_ACCESS_TOKEN)
        if http_res.status != 200:
            raise IoTHttpError(f'api post failed, {http_res.status}, 'f'{url_path}, {data}')

        res_str = await http_res.text()
        res_obj: dict = json.loads(res_str)
        if not res_obj.get('success', None):
            raise IoTHttpError(f'invalid response, {res_obj.get("success", None)}, 'f'{res_obj.get("msg", "")}')
        _LOGGER.debug('api post, %s%s, %s -> %s', self._base_url, url_path, data, res_obj)
        return res_obj

    async def get_devices_async(self) -> dict[str, dict]:
        """获取所有设备."""
        req_params = {
            "isAll": "true",
            "orderBy": "productTypeClass",
            "isShow": "true",
        }
        res_obj = await self.__api_get_async(
            url_path='/api/basic/device/endpoint_page',
            params=req_params
        )
        if 'data' not in res_obj:
            raise IoTHttpError('invalid response result')

        res_obj = res_obj['data']

        # Convert to {mid_bind_id: <info>}
        device_list = {}
        for item in res_obj.get("items", []):
            mid_bind_id = item.get("midBindId", "")
            ep = item.get('endpoint', '')
            if mid_bind_id != "" and ep != '':
                device_list[mid_bind_id].setdefault('sub_devices', {})
                device_list[mid_bind_id]['sub_devices'][ep] = item
        return device_list

    async def ctrl_device_async(self, data: dict) -> None:
        """控制设备."""
        res_obj = await self.__api_post_async(
            url_path='/api/basic/device/ctrl',
            data=data
        )
        if 'data' not in res_obj:
            raise IoTHttpError('invalid response result')
