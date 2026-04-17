# -*- coding: utf-8 -*-
import logging
from typing import Optional

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    SUPPORTED_PLATFORMS
)
from .utils.iot_client import IoTClient, get_iot_instance_async
from .utils.iot_device import IoTDevice
from .utils.iot_error import IoTAuthError, IoTClientError

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, hass_config: dict) -> bool:
    # pylint: disable=unused-argument
    hass.data.setdefault(DOMAIN, {})
    # {[entry_id:str]: IoTClient}, iot client instance
    hass.data[DOMAIN].setdefault('iot_clients', {})
    # {[entry_id:str]: list[IoTDevice]}
    hass.data[DOMAIN].setdefault('devices', {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """设置配置条目."""

    def ha_persistent_notify(
            notify_id: str, title: Optional[str] = None,
            message: Optional[str] = None
    ) -> None:
        """Send messages in Notifications dialog box."""
        if title:
            persistent_notification.async_create(hass=hass, message=message or '', title=title,
                                                 notification_id=notify_id)
        else:
            persistent_notification.async_dismiss(hass=hass, notification_id=notify_id)

    entry_id = config_entry.entry_id
    entry_data = dict(config_entry.data)

    ha_persistent_notify(notify_id=f'{entry_id}.auth_error', title=None, message=None)

    try:
        iot_client: IoTClient = await get_iot_instance_async(
            hass=hass,
            entry_id=entry_id,
            entry_data=entry_data,
            persistent_notify=ha_persistent_notify
        )
        iot_devices: list[IoTDevice] = []
        for mid_bind_id, info in iot_client.device_list.items():
            device: IoTDevice = IoTDevice(
                iot_client=iot_client,
                device_info={
                    **info,
                    'manufacturer': "艾美科技"
                })
            iot_devices.append(device)

        hass.data[DOMAIN]['devices'][config_entry.entry_id] = iot_devices
        # 设置平台
        await hass.config_entries.async_forward_entry_setups(config_entry, SUPPORTED_PLATFORMS)
    except IoTAuthError as auth_error:
        ha_persistent_notify(
            notify_id=f'{entry_id}.auth_error',
            title='AAM Auth Error',
            message=f'Please re-add.\r\nerror: {auth_error}'
        )
    except Exception as err:
        raise err

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """卸载配置条目."""
    entry_id = config_entry.entry_id
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, SUPPORTED_PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN]['devices'].pop(entry_id, None)

    # Remove integration data
    iot_client: IoTClient = hass.data[DOMAIN]['iot_clients'].pop(entry_id, None)
    if iot_client:
        await iot_client.de_init_async()
    del iot_client

    return True
