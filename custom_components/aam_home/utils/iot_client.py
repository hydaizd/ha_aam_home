# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import Optional, Callable

from homeassistant.core import HomeAssistant

from .http_client import IoTHttpClient, IoTAuthClient
from .iot_error import IoTClientError
from .iot_storage import IoTStorage
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class IoTClient:
    """IoT client instance."""
    # pylint: disable=unused-argument
    # pylint: disable=broad-exception-caught
    # pylint: disable=inconsistent-quotes
    _main_loop: asyncio.AbstractEventLoop
    _storage: IoTStorage

    _uname: str
    _entry_id: str
    _entry_data: dict
    _host: str
    # IoT oauth client
    _auth: Optional[IoTAuthClient]
    # IoT http client
    _http: Optional[IoTHttpClient]
    # User config, store in the .storage/aam_home
    _user_config: Optional[dict]

    # Device list, {mid_bind_id: <info>}
    _device_list: dict[str, dict]

    def __init__(self, entry_id: str, entry_data: dict, storage: IoTStorage,
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        # MUST run in a running event loop
        self._main_loop = loop or asyncio.get_running_loop()
        # Check params
        if not isinstance(entry_data, dict):
            raise IoTClientError('invalid entry data')

        self._entry_id = entry_id
        self._entry_data = entry_data
        self._uname = entry_data.get('username')
        self._host = entry_data.get('host')
        self._storage = storage
        self._auth = None
        self._http = None
        self._user_config = None
        self._device_list = {}

    async def de_init_async(self) -> None:
        _LOGGER.info('de_init_async')

    @property
    def main_loop(self) -> asyncio.AbstractEventLoop:
        return self._main_loop

    async def init_async(self) -> None:
        """Init IoT client."""
        # Load user config and check
        self._user_config = await self._storage.load_user_config_async(uname=self._uname, host=self._host)
        if not self._user_config:
            # Integration need to be add again
            raise IoTClientError('load_user_config_async error')

        self._auth = IoTAuthClient(
            host=self._entry_data.get('host'),
            username=self._entry_data.get('username'),
            password=self._entry_data.get('password'),
            loop=self._main_loop)

        # IoT http client instance
        self._http = IoTHttpClient(
            host=self._entry_data.get('host'),
            access_token=self._user_config['auth_info']['access_token'],
            loop=self._main_loop)

        # Load device list
        self._device_list = await self._http.get_devices_async()

    @property
    def host(self) -> str:
        return self._host

    @property
    def device_list(self) -> dict[str, dict]:
        return self._device_list

    async def ctrl_device_async(self, cmd: str, mid_bind_id: str, endpoint: str, group_id: str,
                                json_data: dict) -> bool:
        """设备控制."""
        if f'{mid_bind_id}_{endpoint}' not in self._device_list:
            raise IoTClientError(f'device not exist, {mid_bind_id}_{endpoint}')

        req_data = {
            "cmd": cmd,
            "endpointId": endpoint,
            "groupId": group_id,
            "jsonData": json_data,
            "midBindId": mid_bind_id,
        }
        result = await self._http.ctrl_device_async(data=req_data)
        _LOGGER.debug('ctrl: %s, %s.%s, %s -> %s', cmd, mid_bind_id, endpoint, json_data, result)
        return True


@staticmethod
async def get_iot_instance_async(
        hass: HomeAssistant,
        entry_id: str,
        entry_data: Optional[dict] = None,
        persistent_notify: Optional[Callable[[str, str, str], None]] = None
) -> IoTClient:
    """Get IoT client instance."""
    if entry_id is None:
        raise IoTClientError('invalid entry_id')
    iot_client = hass.data[DOMAIN].get('iot_clients', {}).get(entry_id, None)
    if iot_client:
        _LOGGER.info('instance exist, %s', entry_id)
        return iot_client

    # Create new instance
    if not entry_data:
        raise IoTClientError('entry data is None')

    # Get running loop
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    if not loop:
        raise IoTClientError('loop is None')

    # IoT storage
    storage: Optional[IoTStorage] = hass.data[DOMAIN].get('iot_storage', None)
    if not storage:
        storage = IoTStorage(root_path=entry_data['storage_path'], loop=loop)
        hass.data[DOMAIN]['iot_storage'] = storage
        _LOGGER.info('create iot_storage instance')

    # IoT client
    iot_client = IoTClient(
        entry_id=entry_id,
        entry_data=entry_data,
        storage=storage,
        loop=loop
    )
    iot_client.persistent_notify = persistent_notify
    hass.data[DOMAIN]['iot_clients'].setdefault(entry_id, iot_client)
    _LOGGER.info('new iot_client instance, %s, %s', entry_id, entry_data)
    await iot_client.init_async()
    return iot_client
