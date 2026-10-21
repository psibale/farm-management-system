"""Small signature-based cache for read-only Excel workbook loads."""

import copy
import os
import pickle
import threading
from collections import OrderedDict

import pandas as pd


_CACHE = OrderedDict()
_CACHE_LOCK = threading.RLock()
_PATH_LOCKS = {}
_CACHE_LIMIT = 64


def _copy_result(value):
    if isinstance(value, pd.DataFrame):
        return value.copy(deep=True)
    if isinstance(value, pd.Series):
        return value.copy(deep=True)
    if isinstance(value, dict):
        return {key: _copy_result(item) for key, item in value.items()}
    return copy.deepcopy(value)


def read_excel_cached(path, *args, **kwargs):
    """Read a workbook and cache it until its file or read options change.

    Only filesystem paths are cached. File-like objects and other inputs are
    passed directly to pandas. Returned objects are copies, so callers can
    safely filter or modify them without changing the cached workbook.
    """
    try:
        file_path = os.path.abspath(os.fspath(path))
        stat = os.stat(file_path)
        signature = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
        try:
            options_key = pickle.dumps((args, kwargs), protocol=4)
        except Exception:
            options_key = repr((args, kwargs)).encode("utf-8", errors="replace")
        cache_key = (file_path, signature, options_key)
    except (TypeError, ValueError, OSError):
        return pd.read_excel(path, *args, **kwargs)

    with _CACHE_LOCK:
        path_lock = _PATH_LOCKS.setdefault(file_path, threading.Lock())

    # Calls for different workbooks can parse concurrently; calls for the same
    # workbook share one parse and then reuse its cached copy.
    with path_lock:
        with _CACHE_LOCK:
            cached = _CACHE.get(cache_key)
            if cached is not None:
                _CACHE.move_to_end(cache_key)
                cached_copy = _copy_result(cached)
            else:
                cached_copy = None
        if cached_copy is not None:
            return cached_copy

        result = pd.read_excel(file_path, *args, **kwargs)
        try:
            stat_after = os.stat(file_path)
            signature_after = (stat_after.st_mtime_ns, stat_after.st_ctime_ns, stat_after.st_size)
        except OSError:
            signature_after = None
        if signature_after == signature:
            with _CACHE_LOCK:
                _CACHE[cache_key] = _copy_result(result)
                _CACHE.move_to_end(cache_key)
                while len(_CACHE) > _CACHE_LIMIT:
                    _CACHE.popitem(last=False)
        return result
