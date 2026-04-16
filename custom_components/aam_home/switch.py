# -*- coding: utf-8 -*-
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DATA_API_CLIENT, DATA_COORDINATOR, TEST_DEVICE_ID
from .utils.local_api import LocalAPI

# 用于在 HA 前端显示的名称
DEFAULT_NAME = "Aam Home Controlled Switch"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """设置开关平台."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    api: LocalAPI = data[DATA_API_CLIENT]
    coordinator = data[DATA_COORDINATOR]

    # 从协调器获取设备数据
    devices = coordinator.data.get("devices", [])

    # 创建开关实体
    entities = []
    for device in devices:
        product_key = device.get("productKey", "")
        if product_key in ["7504"]:  # 空开设备
            entities.append(
                AamSwitchEntity(
                    coordinator,
                    api,
                    device,
                    config_entry.entry_id
                )
            )

    async_add_entities(entities)


class AamSwitchEntity(CoordinatorEntity, SwitchEntity):
    """表示智能盒子开关实体."""

    def __init__(
            self,
            coordinator,
            api: LocalAPI,
            device: dict[str, Any],
            entry_id: str
    ) -> None:
        """初始化开关."""
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._entry_id = entry_id

        # 设备属性
        self._attr_name = device.get("name", f"开关 {device.get('endpointId')}")
        self._attr_unique_id = f"{entry_id}_{device.get('midBindId')}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": f"智能盒子 {entry_id}",
            "manufacturer": "智能盒子厂商",
            "model": "智能控制盒"
        }

        # 从设备数据初始化状态
        self._attr_is_on = device.get("state", 0) == 1

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """返回设备额外属性."""
        return {
            "endpoint_id": self._device.get("endpointId"),
            "group_id": self._device.get("groupId"),
            "mid_bind_id": self._device.get("midBindId"),
            "product_key": self._device.get("productKey"),
            "firmware_version": self._device.get("version", "unknown")
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """打开开关."""
        success = await self._api.async_control_device(
            endpoint_id=self._device.get("endpointId"),
            group_id=self._device.get("groupId"),
            mid_bind_id=self._device.get("midBindId"),
            state=1
        )

        if success:
            self._attr_is_on = True
            self.async_write_ha_state()

            # 触发协调器更新
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("无法打开开关: %s", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭开关."""
        success = await self._api.async_control_device(
            endpoint_id=self._device.get("endpointId"),
            group_id=self._device.get("groupId"),
            mid_bind_id=self._device.get("midBindId"),
            state=0
        )

        if success:
            self._attr_is_on = False
            self.async_write_ha_state()

            # 触发协调器更新
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("无法关闭开关: %s", self._attr_name)

    def _handle_coordinator_update(self) -> None:
        """处理协调器更新."""
        # 从最新数据中查找当前设备状态
        devices = self.coordinator.data.get("devices", [])
        for device in devices:
            if device.get("midBindId") == self._device.get("midBindId"):
                self._device = device
                self._attr_is_on = device.get("state", 0) == 1
                break

        self.async_write_ha_state()
