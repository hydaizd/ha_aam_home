# -*- coding: utf-8 -*-
from enum import Enum
from typing import Any


class IoTErrorCode(Enum):
    """IoT error code."""
    CODE_UNKNOWN = -10000
    CODE_HTTP_INVALID_ACCESS_TOKEN = -10030


class IoTError(Exception):
    """IoT error."""
    code: IoTErrorCode
    message: Any

    def __init__(self, message: Any, code: IoTErrorCode = IoTErrorCode.CODE_UNKNOWN) -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)

    def to_str(self) -> str:
        return f'{{"code":{self.code.value},"message":"{self.message}"}}'

    def to_dict(self) -> dict:
        return {"code": self.code.value, "message": self.message}


class IoTAuthError(IoTError):
    ...


class IoTHttpError(IoTError):
    ...


class IoTClientError(IoTError):
    ...


class IoTConfigError(IoTError):
    ...


class IoTSpecError(IoTError):
    ...


class IoTDeviceError(IoTError):
    ...
