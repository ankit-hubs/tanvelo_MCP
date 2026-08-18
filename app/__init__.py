"""Tanvelo - Universal AI Memory Layer"""

import os
import ctypes

# Preload libstdc++.so.6 if required in minimal nix environments without polluting shell LD_LIBRARY_PATH
_candidates = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv/lib/libstdc++.so.6"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv/lib/python3.11/site-packages/libstdc++.so.6"),
    "/nix/store/03h8f1wmpb86s9v8xd0lcb7jnp7nwm6l-idx-env-fhs/usr/lib/libstdc++.so.6",
    "/nix/store/09kfkia2q352fqdj7g2bf6aljzb85rx2-idx-env-fhs/usr/lib/libstdc++.so.6",
]

for _p in _candidates:
    if os.path.exists(_p):
        try:
            ctypes.CDLL(_p)
            break
        except Exception:
            pass

__version__ = "1.0.0"
