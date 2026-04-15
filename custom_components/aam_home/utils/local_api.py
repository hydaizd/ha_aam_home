"""API client for Local."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from ..const import (
    API_LOGIN,
    API_DEVICES,
    API_CONTROL
)

_LOGGER = logging.getLogger(__name__)


class LocalAPI:
    """智能盒子API客户端."""

    def __init__(
            self,
            host: str,
            username: str,
            password: str,
            session: aiohttp.ClientSession,
            timeout: int = 10
    ) -> None:
        """初始化API客户端."""
        self._host = host.rstrip("/")
        self._username = username
        self._password = password
        self._session = session
        self._timeout = timeout
        self._token = None
        self._devices = []

    async def async_login(self) -> bool:
        """登录到智能盒子."""
        url = f"{self._host}/{API_LOGIN.lstrip('/')}"
        payload = {
            "username": self._username,
            "password": self._password
        }

        try:
            async with asyncio.timeout(self._timeout):
                response = await self._session.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status == 200:
                    data = await response.json()
                    # 登录成功
                    if data.get("success"):
                        self._token = data.get("data")
                        return True
                    else:
                        _LOGGER.error("登录失败: %s", data.get("msg"))
                        return False
                else:
                    _LOGGER.error("登录失败: %s", response.status)
                    return False

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("连接错误: %s", err)
            return False

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """获取所有设备列表."""
        if not self._token:
            if not await self.async_login():
                return []

        url = f"{self._host}/{API_DEVICES.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

        try:
            async with asyncio.timeout(self._timeout):
                response = await self._session.get(url, headers=headers)

                if response.status == 200:
                    data = await response.json()
                    self._devices = data.get("devices", [])
                    return self._devices
                elif response.status == 401:
                    # Token过期，重新登录
                    if await self.async_login():
                        return await self.async_get_devices()
                    else:
                        return []
                else:
                    _LOGGER.error("获取设备失败: %s", response.status)
                    return []

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("获取设备错误: %s", err)
            return []

    async def async_control_device(
            self,
            endpoint_id: str,
            group_id: str,
            mid_bind_id: str,
            state: int
    ) -> bool:
        """控制设备开关状态."""
        if not self._token:
            if not await self.async_login():
                return False

        url = f"{self._host}/{API_CONTROL.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

        payload = {
            "cmd": "set_state",
            "endpointId": endpoint_id,
            "groupId": group_id,
            "jsonData": {"State": state},
            "midBindId": mid_bind_id
        }

        try:
            async with asyncio.timeout(self._timeout):
                response = await self._session.post(
                    url,
                    json=payload,
                    headers=headers
                )

                if response.status == 200:
                    data = await response.json()
                    return data.get("success", False)
                elif response.status == 401:
                    # Token过期，重新登录后重试
                    if await self.async_login():
                        return await self.async_control_device(
                            endpoint_id, group_id, mid_bind_id, state
                        )
                    else:
                        return False
                else:
                    _LOGGER.error("控制设备失败: %s", response.status)
                    return False

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("控制设备错误: %s", err)
            return False

    async def async_get_device_status(self, device_id: str) -> dict[str, Any] | None:
        """获取单个设备状态."""
        if not self._devices:
            await self.async_get_devices()

        for device in self._devices:
            if device.get("midBindId") == device_id:
                return device

        return None
