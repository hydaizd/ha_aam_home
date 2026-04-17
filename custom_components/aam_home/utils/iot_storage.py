# -*- coding: utf-8 -*-
import asyncio
import hashlib
import json
import logging
import os
import traceback
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Any, Union

_LOGGER = logging.getLogger(__name__)


class IoTStorageType(Enum):
    LOAD = auto()
    LOAD_FILE = auto()
    SAVE = auto()
    SAVE_FILE = auto()
    DEL = auto()
    DEL_FILE = auto()
    CLEAR = auto()


class IoTStorage:
    """
    File management.
    User data will be stored in the `.storage` directory of Home Assistant.
    """
    _main_loop: asyncio.AbstractEventLoop
    _file_future: dict[str, tuple[IoTStorageType, asyncio.Future]]

    _root_path: str

    def __init__(self, root_path: str, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Initialize with a root path."""
        self._main_loop = loop or asyncio.get_running_loop()
        self._file_future = {}

        self._root_path = os.path.abspath(root_path)
        os.makedirs(self._root_path, exist_ok=True)

        _LOGGER.debug('root path, %s', self._root_path)

    def __get_full_path(self, domain: str, name: str, suffix: str) -> str:
        return os.path.join(self._root_path, domain, f'{name}.{suffix}')

    async def update_user_config_async(self, username: str, host: str, config: Optional[dict[str, Any]],
                                       replace: bool = False) -> bool:
        """Update user configuration."""
        if config is not None and len(config) == 0:
            # Do nothing
            return True

        config_domain = 'iot_config'
        config_name = f'{username}_{host}'
        if config is None:
            # Remove config file
            return await self.remove_async(domain=config_domain, name=config_name, type_=dict)
        if replace:
            # Replace config file
            return await self.save_async(domain=config_domain, name=config_name, data=config)
        local_config = (await self.load_async(domain=config_domain, name=config_name, type_=dict)) or {}
        local_config.update(config)  # type: ignore
        return await self.save_async(domain=config_domain, name=config_name, data=local_config)

    async def remove_async(self, domain: str, name: str, type_: type) -> bool:
        full_path = self.__get_full_path(domain=domain, name=name, suffix=type_.__name__)
        if full_path in self._file_future:
            # Waiting for the last task to be completed
            op_type, fut = self._file_future[full_path]
            if op_type == IoTStorageType.DEL:
                if not fut.done():
                    return await fut
            else:
                await fut
        fut = self._main_loop.run_in_executor(None, self.__remove, full_path)
        if not fut.done():
            self.__add_file_future(full_path, IoTStorageType.DEL, fut)
        return await fut

    async def save_async(self, domain: str, name: str, data: Union[bytes, str, dict, list, None]) -> bool:
        full_path = self.__get_full_path(domain=domain, name=name, suffix=type(data).__name__)
        if full_path in self._file_future:
            # Waiting for the last task to be completed
            fut = self._file_future[full_path][1]
            await fut
        fut = self._main_loop.run_in_executor(None, self.__save, full_path, data)
        if not fut.done():
            self.__add_file_future(full_path, IoTStorageType.SAVE, fut)
        return await fut

    def __add_file_future(self, key: str, op_type: IoTStorageType, fut: asyncio.Future) -> None:
        def fut_done_callback(fut: asyncio.Future):
            del fut
            self._file_future.pop(key, None)

        fut.add_done_callback(fut_done_callback)
        self._file_future[key] = op_type, fut

    def __save(self, full_path: str, data: Union[bytes, str, dict, list, None], cover: bool = True,
               with_hash: bool = True) -> bool:
        if data is None:
            _LOGGER.error('save error, save data is None')
            return False
        if os.path.exists(full_path):
            if not cover:
                _LOGGER.error('save error, file exists, cover is False')
                return False
            if not os.access(full_path, os.W_OK):
                _LOGGER.error('save error, file not writeable, %s', full_path)
                return False
        else:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
        try:
            w_bytes: bytes
            if isinstance(data, bytes):
                w_bytes = data
            elif isinstance(data, str):
                w_bytes = data.encode('utf-8')
            elif isinstance(data, (dict, list)):
                w_bytes = json.dumps(data).encode('utf-8')
            else:
                _LOGGER.error('save error, unsupported data type, %s', type(data).__name__)
                return False
            with open(full_path, 'wb') as w_file:
                w_file.write(w_bytes)
                if with_hash:
                    w_file.write(hashlib.sha256(w_bytes).digest())
            return True
        except (OSError, TypeError) as e:
            _LOGGER.error('save error, %s, %s', e, traceback.format_exc())
            return False

    def __remove(self, full_path: str) -> bool:
        item = Path(full_path)
        if item.is_file() or item.is_symlink():
            item.unlink()
        return True

    async def load_async(self, domain: str, name: str, type_: type = bytes) -> Union[bytes, str, dict, list, None]:
        full_path = self.__get_full_path(domain=domain, name=name, suffix=type_.__name__)
        if full_path in self._file_future:
            # Waiting for the last task to be completed
            op_type, fut = self._file_future[full_path]
            if op_type == IoTStorageType.LOAD:
                if not fut.done():
                    return await fut
            else:
                await fut
        fut = self._main_loop.run_in_executor(None, self.__load, full_path, type_)
        if not fut.done():
            self.__add_file_future(full_path, IoTStorageType.LOAD, fut)
        return await fut

    def __load(self, full_path: str, type_: type = bytes, with_hash_check: bool = True) -> Union[
        bytes, str, dict, list, None]:
        if not os.path.exists(full_path):
            _LOGGER.debug('load error, file does not exist, %s', full_path)
            return None
        if not os.access(full_path, os.R_OK):
            _LOGGER.error('load error, file not readable, %s', full_path)
            return None
        try:
            with open(full_path, 'rb') as r_file:
                r_data: bytes = r_file.read()
                if r_data is None:
                    _LOGGER.error('load error, empty file, %s', full_path)
                    return None
                data_bytes: bytes
                # Hash check
                if with_hash_check:
                    if len(r_data) <= 32:
                        return None
                    data_bytes = r_data[:-32]
                    hash_value = r_data[-32:]
                    if hashlib.sha256(data_bytes).digest() != hash_value:
                        _LOGGER.error('load error, hash check failed, %s', full_path)
                        return None
                else:
                    data_bytes = r_data
                if type_ == bytes:
                    return data_bytes
                if type_ == str:
                    return str(data_bytes, 'utf-8')
                if type_ in [dict, list]:
                    return json.loads(data_bytes)
                _LOGGER.error('load error, unsupported data type, %s', type_.__name__)
                return None
        except (OSError, TypeError) as e:
            _LOGGER.error('load error, %s, %s', e, traceback.format_exc())
            return None
