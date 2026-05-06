# -*- coding: utf-8 -*-
import asyncio
import logging
import traceback
from typing import Any, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from .utils.http_client import IoTAuthClient, IoTHttpClient
from .utils.iot_client import IoTClient
from .utils.iot_client import get_iot_instance_async
from .utils.iot_error import IoTConfigError, IoTError
from .utils.iot_storage import IoTStorage

_LOGGER = logging.getLogger(__name__)


class AamHomeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """处理艾美智空间盒子的配置流程."""
    VERSION = 1

    _config_entry: config_entries.ConfigEntry
    _main_loop: asyncio.AbstractEventLoop
    _iot_client: IoTClient
    _iot_storage: Optional[IoTStorage]
    _iot_auth: Optional[IoTAuthClient]
    _iot_http: Optional[IoTHttpClient]

    _storage_path: str
    _username: str
    _password: str
    _host: str
    _auth_info: dict

    def __init__(self) -> None:
        self._main_loop = asyncio.get_running_loop()
        self._storage_path = ''
        self._host = ''
        self._username = ''
        self._password = ''
        self._auth_info = {}
        self._iot_auth = None
        self._iot_http = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """处理初始步骤."""
        self.hass.data.setdefault(DOMAIN, {})
        if not self._storage_path:
            self._storage_path = self.hass.config.path('.storage', DOMAIN)

        # IoT storage
        self._iot_storage = self.hass.data[DOMAIN].get('iot_storage', None)
        if not self._iot_storage:
            self._iot_storage = IoTStorage(root_path=self._storage_path, loop=self._main_loop)
            self.hass.data[DOMAIN]['iot_storage'] = self._iot_storage
            _LOGGER.info('async_step_user, create iot storage, %s', self._storage_path)

        return await self.async_step_auth_config(user_input)

    async def async_step_auth_config(self, user_input: Optional[dict] = None):
        if user_input:
            self._host = user_input.get(CONF_HOST, self._host)
            self._username = user_input.get(CONF_USERNAME, self._username)
            self._password = user_input.get(CONF_PASSWORD, self._password)

            try:
                return await self.async_step_auth(user_input)
            except Exception as err:
                _LOGGER.error('async_step_auth_config, %s', err)
                return await self.__show_auth_config_form(str(err))
        return await self.__show_auth_config_form('')

    async def async_step_auth(self, user_input: Optional[dict] = None):
        try:
            if not self._iot_auth:
                iot_auth = IoTAuthClient(
                    host=self._host,
                    username=self._username,
                    password=self._password,
                    loop=self._main_loop
                )
                self._iot_auth = iot_auth

            await self.__check_auth_async()
            return await self.config_flow_done()
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error('async_step_auth, %s', err)
            raise err

    async def config_flow_done(self):
        return self.async_create_entry(
            title=f'智空间盒子 ({self._host})',
            data={
                'storage_path': self._storage_path,
                'username': self._username,
                'password': self._password,
                'host': self._host,
            })

    async def __show_auth_config_form(self, reason: str):
        """显示认证配置表单."""
        return self.async_show_form(
            step_id="auth_config",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=""): str,
                vol.Required(CONF_USERNAME, default="admin"): str,
                vol.Required(CONF_PASSWORD, default="admin"): str,
            }),
            errors={"base": reason},
        )

    async def __check_auth_async(self) -> None:
        """检查认证是否成功."""
        if not self._auth_info:
            try:
                if not self._iot_auth:
                    raise IoTConfigError('auth_client_error')
                auth_info = await self._iot_auth.get_access_token_async()
                if not self._iot_http:
                    self._iot_http = IoTHttpClient(host=self._host, access_token=auth_info['access_token'])
                else:
                    self._iot_http.update_http_header(access_token=auth_info['access_token'])
                self._auth_info = auth_info
            except Exception as err:
                _LOGGER.error('get_access_token, %s, %s', err, traceback.format_exc())
                raise IoTConfigError('get_token_error') from err

        try:
            # Save auth_info
            if not (await self._iot_storage.update_user_config_async(
                    uname=self._username, host=self._host, config={
                        'auth_info': self._auth_info
                    })):
                raise IoTError('iot_storage.update_user_config_async error')
        except Exception as err:
            _LOGGER.error('save_auth_info error, %s, %s', err, traceback.format_exc())
            raise IoTConfigError('save_auth_info_error') from err

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """ 使用户能够在 UI 界面上随时修改已配置集成的可选参数。 """
    # pylint: disable=unused-argument
    # pylint: disable=inconsistent-quotes
    _config_entry: config_entries.ConfigEntry
    _main_loop: asyncio.AbstractEventLoop
    _iot_client: IoTClient

    _iot_storage: IoTStorage

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self._config_entry = config_entry
        self._main_loop = asyncio.get_event_loop()

        _LOGGER.info('options init, %s, %s, %s, %s', config_entry.entry_id, config_entry.unique_id, config_entry.data,
                     config_entry.options)

    async def async_step_init(self, user_input=None):
        """初始化选项流程."""
        self.hass.data.setdefault(DOMAIN, {})

        try:
            # IoT client
            self._iot_client = await get_iot_instance_async(
                hass=self.hass, entry_id=self._config_entry.entry_id)
            if not self._iot_client:
                raise IoTConfigError('invalid miot client')

            # IoT storage
            self._iot_storage = self._iot_client._storage
            if not self._iot_storage:
                raise IoTConfigError('invalid miot storage')

            # Check token
            if not await self._iot_client.refresh_auth_info_async():
                _LOGGER.info('refresh auth info error')

            return await self.async_step_config_options()

        except IoTConfigError as err:
            raise AbortFlow(reason='options_flow_error', description_placeholders={'error': str(err)}) from err
        except AbortFlow as err:
            raise err
        except Exception as err:
            _LOGGER.error('async_step_init error, %s, %s', err, traceback.format_exc())
            raise AbortFlow(reason='re_add', description_placeholders={'error': str(err)}) from err
