import importlib.util
import re
from pathlib import Path

import pandas as pd
import pytest

BUILD_MOD = Path(__file__).resolve().parents[1] / "mod" / "build_mod.py"
spec = importlib.util.spec_from_file_location("build_mod", BUILD_MOD)
build_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_mod)


def test_advice_dict_orders_by_rank():
    recs = pd.DataFrame({
        "map_name": ["m", "m", "m"], "team": [1, 1, 2], "rank": [2, 1, 1],
        "center_x": [150.0, -50.0, 0.0], "center_z": [250.0, 50.0, 0.0],
    })
    assert build_mod.advice_dict(recs) == {"m": {"1": [[-50.0, 50.0], [150.0, 250.0]], "2": [[0.0, 0.0]]}}


def test_mod_source_has_one_placeholder():
    source = build_mod.SOURCE.read_text(encoding="utf-8")
    assert source.count(build_mod.PLACEHOLDER) == 1
    rendered = build_mod.render_source({"m": {"1": [[1.0, 2.0]]}})
    assert "ADVICE = {'m': {'1': [[1.0, 2.0]]}}" in rendered


def test_mod_source_is_python27_friendly():
    source = build_mod.SOURCE.read_text(encoding="utf-8")
    compile(source, "mod_spawn_advisor.py", "exec")
    assert "from __future__ import print_function" in source
    assert not re.search(r"\bf['\"]", source)               # f-строк нет в Python 2.7
