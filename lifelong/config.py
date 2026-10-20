"""YAML config loading with single inheritance (`base: other.yaml`)."""
import os

import yaml


def _merge(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config(path):
    with open(path) as f:
        cfg = yaml.safe_load(f)
    base = cfg.pop("base", None)
    if base:
        cfg = _merge(load_config(os.path.join(os.path.dirname(path), base)), cfg)
    return cfg
