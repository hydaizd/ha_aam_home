# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import Optional, Callable

from homeassistant.core import HomeAssistant

from .http_client import IoTHttpClient, IoTAuthClient
from .iot_device import IoTDevice
from .iot_error import IoTClientError
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class IoTClient:
    """IoT client instance."""
    # pylint: disable=unused-argument
    # pylint: disable=broad-exception-caught
    # pylint: disable=inconsistent-quotes
    _main_loop: asyncio.AbstractEventLoop

    _entry_id: str
    _entry_data: dict
    # MIoT oauth client
    _auth: Optional[IoTAuthClient]
    # IoT http client
    _http: Optional[IoTHttpClient]
    # User config, store in the .storage/aam_home
    _user_config: Optional[dict]

    # Device list, {mid_bind_id: <info>}
    _device_list: dict[str, dict]

    def __init__(self, entry_id: str, entry_data: dict, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        # MUST run in a running event loop
        self._main_loop = loop or asyncio.get_running_loop()
        # Check params
        if not isinstance(entry_data, dict):
            raise IoTClientError('invalid entry data')

        self._entry_id = entry_id
        self._entry_data = entry_data
        self._auth = None
        self._http = None
        self._user_config = None
        self._device_list = {}

    async def de_init_async(self) -> None:
        _LOGGER.info('de_init_async')

    async def init_async(self) -> None:
        """Init IoT client."""
        # Load device list
        self._device_list = await self._http.get_devices_async()

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

    @property
    def device_list(self) -> dict:
        return self._device_list

    async def ctrl_device_async(self, iot_device: IoTDevice, cmd: str, json_data: dict) -> bool:
        """设备控制."""
        if iot_device.mid_bind_id not in self._device_list:
            raise IoTClientError(f'device not exist, {iot_device.mid_bind_id}')

        req_data = {
            "cmd": cmd,
            "endpointId": iot_device.endpoint,
            "groupId": iot_device.endpoint,
            "jsonData": json_data,
            "midBindId": iot_device.mid_bind_id,
        }
        result = await self._http.ctrl_device_async(data=req_data)
        _LOGGER.debug('ctrl: %s, %s.%s, %s -> %s', cmd, iot_device.mid_bind_id, iot_device.endpoint, json_data, result)
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

    # IoT client
    iot_client = IoTClient(
        entry_id=entry_id,
        entry_data=entry_data,
        loop=loop
    )
    iot_client.persistent_notify = persistent_notify
    hass.data[DOMAIN]['iot_clients'].setdefault(entry_id, iot_client)
    _LOGGER.info('new iot_client instance, %s, %s', entry_id, entry_data)
    await iot_client.init_async()
    return iot_client
