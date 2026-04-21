# -*- coding: utf-8 -*-
from slugify import slugify


def slugify_did(host: str, mid_bind_id: str) -> str:
    """Slugify a device id."""
    return slugify(f'{host}_{mid_bind_id}', separator='_')


def slugify_name(name: str, separator: str = '_') -> str:
    """Slugify a name."""
    return slugify(name, separator=separator)
