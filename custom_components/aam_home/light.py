import logging
from typing import Any

from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DATA_API_CLIENT, DATA_COORDINATOR
from .utils.local_api import LocalAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """设置灯光平台."""
    data = hass.data[DOMAIN][entry.entry_id]
    api: LocalAPI = data[DATA_API_CLIENT]
    coordinator = data[DATA_COORDINATOR]

    # 从协调器获取设备数据
    devices = coordinator.data.get("devices", [])

    # 创建灯光实体
    entities = []
    for device in devices:
        device_type = device.get("type", "")
        if device_type == "light":  # 灯光设备
            entities.append(
                AamLightEntity(
                    coordinator,
                    api,
                    device,
                    entry.entry_id
                )
            )

    async_add_entities(entities)


class AamLightEntity(CoordinatorEntity, LightEntity):
    """表示智能盒子灯光实体."""

    def __init__(
            self,
            coordinator,
            api: LocalAPI,
            device: dict[str, Any],
            entry_id: str
    ) -> None:
        """初始化灯光."""
        super().__init__(coordinator)
        self._api = api
        self._device = device
        self._entry_id = entry_id

        # 设备属性
        self._attr_name = device.get("name", f"灯光 {device.get('endpointId')}")
        self._attr_unique_id = f"{entry_id}_light_{device.get('midBindId')}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": f"智能盒子 {entry_id}",
            "manufacturer": "智能盒子厂商",
            "model": "智能控制盒"
        }

        # 从设备数据初始化状态
        self._attr_is_on = device.get("state", 0) == 1
        self._attr_brightness = device.get("brightness", 255)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """返回设备额外属性."""
        attrs = {
            "endpoint_id": self._device.get("endpointId"),
            "group_id": self._device.get("groupId"),
            "mid_bind_id": self._device.get("midBindId"),
            "device_type": self._device.get("type"),
            "firmware_version": self._device.get("firmwareVersion", "unknown")
        }

        # 添加灯光特有属性
        if "color_temp" in self._device:
            attrs["color_temp"] = self._device.get("color_temp")
        if "rgb_color" in self._device:
            attrs["rgb_color"] = self._device.get("rgb_color")

        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        """打开灯光."""
        # 构建控制命令
        json_data = {"State": 1}

        # 处理亮度
        if "brightness" in kwargs:
            brightness = kwargs["brightness"]
            json_data["Brightness"] = brightness
            self._attr_brightness = brightness

        # 处理颜色温度
        if "color_temp" in kwargs:
            color_temp = kwargs["color_temp"]
            json_data["ColorTemp"] = color_temp

        # 处理RGB颜色
        if "rgb_color" in kwargs:
            rgb_color = kwargs["rgb_color"]
            json_data["RGB"] = rgb_color

        # 发送控制命令
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
            _LOGGER.error("无法打开灯光: %s", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭灯光."""
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
            _LOGGER.error("无法关闭灯光: %s", self._attr_name)

    def _handle_coordinator_update(self) -> None:
        """处理协调器更新."""
        # 从最新数据中查找当前设备状态
        devices = self.coordinator.data.get("devices", [])
        for device in devices:
            if device.get("midBindId") == self._device.get("midBindId"):
                self._device = device
                self._attr_is_on = device.get("state", 0) == 1
                self._attr_brightness = device.get("brightness", 255)
                break

        self.async_write_ha_state()
