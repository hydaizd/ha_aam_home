# -*- coding: utf-8 -*-

DOMAIN: str = "aam_home"
NAME: str = "艾美智空间设备控制器"

# 　定义集成支持的平台
SUPPORTED_PLATFORMS: list = [
    "switch",
]

# 配置键
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# API端点
API_LOGIN = "/api/basic/user/login"
API_DEVICES = "/api/basic/device/endpoint_page"
API_CONTROL = "/api/basic/device/ctrl"

# 默认值
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_TIMEOUT = 10

# 数据存储键
DATA_API_CLIENT = "api_client"
DATA_COORDINATOR = "coordinator"

# 指定测试设备
TEST_DEVICE_ID: list = [
    "70B3D5058043552C"
]
