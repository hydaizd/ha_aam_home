# -*- coding: utf-8 -*-

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_USERNAME,
    CONF_PASSWORD,
    DATA_COORDINATOR,
    DATA_API_CLIENT,
    DEFAULT_SCAN_INTERVAL,
    SUPPORTED_PLATFORMS
)
from .utils.local_api import LocalAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """设置配置条目."""
    hass.data.setdefault(DOMAIN, {})

    # 创建API客户端
    session = hass.helpers.aiohttp_client.async_get_clientsession()
    api = LocalAPI(
        host=config_entry.data[CONF_HOST],
        username=config_entry.data[CONF_USERNAME],
        password=config_entry.data[CONF_PASSWORD],
        session=session
    )

    # 登录并获取初始设备列表
    if not await api.async_login():
        _LOGGER.error("无法登录到智能盒子")
        return False

    # 创建数据更新协调器[4](@ref)
    async def async_update_data():
        """从API获取最新数据."""
        devices = await api.async_get_devices()
        return {"devices": devices}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="my_smart_box",
        update_method=async_update_data,
        update_interval=DEFAULT_SCAN_INTERVAL,
    )

    # 获取初始数据
    await coordinator.async_config_entry_first_refresh()

    # 存储数据
    hass.data[DOMAIN][config_entry.entry_id] = {
        DATA_API_CLIENT: api,
        DATA_COORDINATOR: coordinator
    }

    # 设置平台
    await hass.config_entries.async_forward_entry_setups(config_entry, SUPPORTED_PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """卸载配置条目."""
    if unload_ok := await hass.config_entries.async_unload_platforms(config_entry, SUPPORTED_PLATFORMS):
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok
