# -*- coding: utf-8 -*-

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from .utils.local_api import LocalAPI

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """验证用户输入并登录盒子."""
    session = async_get_clientsession(hass)
    api = LocalAPI(
        host=data[CONF_HOST],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        session=session
    )

    # 尝试登录
    if not await api.async_login():
        raise InvalidAuth

    # 获取设备列表验证连接
    devices = await api.async_get_devices()
    if not devices:
        raise CannotConnect

    return {"title": f"智能盒子 ({data[CONF_HOST]})"}


class AamHomeConfigFlow(ConfigFlow, domain=DOMAIN):
    """处理艾美智空间盒子的配置流程."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """处理初始步骤."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        """Handle user flow."""
        if user_input:
            if user_input["host"]:
                return await self.async_step_device()
            return await self.async_step_configure()

        # 显示配置表单
        data_schema = vol.Schema({
            vol.Required(CONF_HOST, default=""): str,
            vol.Required(CONF_USERNAME, default="admin"): str,
            vol.Required(CONF_PASSWORD, default="admin"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """无法连接到盒子时抛出错误."""


class InvalidAuth(HomeAssistantError):
    """认证失败时抛出错误."""
