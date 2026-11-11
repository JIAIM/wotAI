"""Сборка мода: советы из recommendations.parquet → в код мода, компиляция Python 2.7,
упаковка в .wotmod (ZIP без сжатия).

Запуск из корня проекта (Python 3, ваша .venv):
    python mod/build_mod.py
Если Python 2.7 вызывается не через «py -2.7», передайте путь к python.exe 2.7:
    python mod/build_mod.py C:\\Python27\\python.exe
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pandas as pd

MOD_DIR = Path(__file__).resolve().parent
SOURCE = MOD_DIR / "mod_spawn_advisor.py"
META = MOD_DIR / "meta.xml"
RECS = MOD_DIR.parent / "data" / "processed" / "recommendations.parquet"
BUILD = MOD_DIR.parent / "build"
DIST = MOD_DIR.parent / "dist"
INNER_PATH = "res/scripts/client/gui/mods/mod_spawn_advisor.pyc"
PLACEHOLDER = "ADVICE = {}"


def advice_dict(recs: pd.DataFrame) -> dict:
    """{карта: {"сторона": [[x, z], ...] в порядке места}}"""
    advice = {}
    for (map_name, team), group in recs.sort_values("rank").groupby(["map_name", "team"]):
        points = [[round(float(x), 1), round(float(z), 1)] for x, z in zip(group["center_x"], group["center_z"])]
        advice.setdefault(str(map_name), {})[str(int(team))] = points
    return advice


def render_source(advice: dict) -> str:
    source = SOURCE.read_text(encoding="utf-8")
    if source.count(PLACEHOLDER) != 1:
        raise RuntimeError(f"в {SOURCE.name} должна быть ровно одна строка «{PLACEHOLDER}»")
    return source.replace(PLACEHOLDER, "ADVICE = " + repr(advice))


def compile_py27(source_file: Path, python27: str | None) -> Path:
    command = [python27] if python27 else ["py", "-2.7"]
    subprocess.run(command + ["-m", "py_compile", str(source_file)], check=True)
    compiled = source_file.with_suffix(".pyc")
    if not compiled.exists():
        raise FileNotFoundError(f"{compiled} не появился: проверьте, что компилировал именно Python 2.7")
    with compiled.open("rb") as f:
        magic = f.read(4)
    if magic != b"\x03\xf3\r\n":
        raise RuntimeError(f"{compiled} собран не Python 2.7 (magic {magic!r})")
    return compiled


def build(python27: str | None = None) -> Path:
    version = ET.parse(META).getroot().findtext("version")
    advice = advice_dict(pd.read_parquet(RECS))

    BUILD.mkdir(exist_ok=True)
    rendered = BUILD / SOURCE.name
    rendered.write_text(render_source(advice), encoding="utf-8")
    compiled = compile_py27(rendered, python27)

    DIST.mkdir(exist_ok=True)
    output = DIST / f"spawn_advisor_{version}.wotmod"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as wotmod:
        wotmod.write(META, "meta.xml")
        wotmod.write(compiled, INNER_PATH)
    print(f"советы: {len(advice)} карт")
    return output


if __name__ == "__main__":
    result = build(sys.argv[1] if len(sys.argv) > 1 else None)
    print("готово:", result)
    print("скопируйте его в World_of_Tanks\\mods\\<номер версии игры>\\ и удалите старую версию мода")
