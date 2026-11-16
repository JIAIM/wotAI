"""Сборка релиза одной командой: реплеи → датасет → признаки → советы → .wotmod.

Запуск из корня проекта:
    python -m spawn_advisor.release                 # всё заново (реплеи из кэша парсера)
    python -m spawn_advisor.release --skip-dataset  # взять готовые dataset/roster.parquet
    python -m spawn_advisor.release --python27 C:\\Python27\\python.exe

Танкопедия берётся из data/processed/tankopedia.parquet; если файла нет — скачивается
через WG API (нужен WG_APPLICATION_ID в .env).
"""
import argparse
import importlib.util
from pathlib import Path

import pandas as pd

from spawn_advisor.dataset import PARSER_VERSION, build_dataset
from spawn_advisor.features import build_features
from spawn_advisor.recommend import build_recommendations

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
CACHE = Path("data/interim") / f"parser_{PARSER_VERSION}"
BUILD_MOD = Path("mod/build_mod.py")


def step(title):
    print(f"\n=== {title} ===")


def load_tankopedia() -> pd.DataFrame:
    path = PROCESSED / "tankopedia.parquet"
    if path.exists():
        return pd.read_parquet(path)
    from spawn_advisor.tankopedia import fetch_vehicles, get_application_id, to_table
    tanks = to_table(fetch_vehicles(get_application_id()))
    tanks.to_parquet(path, index=False)
    return tanks


def build_mod(python27):
    """mod/build_mod.py — не часть пакета, поэтому загружаем его по пути."""
    spec = importlib.util.spec_from_file_location("build_mod", BUILD_MOD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build(python27)


def main():
    parser = argparse.ArgumentParser(description="Пересобрать советы и мод")
    parser.add_argument("--skip-dataset", action="store_true", help="не разбирать реплеи, взять готовые parquet")
    parser.add_argument("--python27", default=None, help="путь к python.exe 2.7 (по умолчанию «py -2.7»)")
    args = parser.parse_args()
    PROCESSED.mkdir(parents=True, exist_ok=True)

    if args.skip_dataset:
        step("1/4 датасет: из готовых файлов")
        df = pd.read_parquet(PROCESSED / "dataset.parquet")
        roster = pd.read_parquet(PROCESSED / "roster.parquet")
    else:
        step("1/4 датасет: разбор реплеев")
        df, roster = build_dataset(RAW, CACHE)
        df.to_parquet(PROCESSED / "dataset.parquet", index=False)
        roster.to_parquet(PROCESSED / "roster.parquet", index=False)
    print(f"строк: {len(df)}, боёв: {df['arena_id'].nunique()}")

    step("2/4 признаки")
    features = build_features(df, roster, load_tankopedia())
    features.to_parquet(PROCESSED / "features.parquet", index=False)
    print(f"строк: {len(features)}, боёв: {features['arena_id'].nunique()}")

    step("3/4 советы")
    recs = build_recommendations(features)
    recs.to_parquet(PROCESSED / "recommendations.parquet", index=False)
    print(f"карт и сторон с советом: {recs.groupby(['map_name', 'team']).ngroups}")

    step("4/4 мод")
    output = build_mod(args.python27)
    print("готово:", output)


if __name__ == "__main__":
    main()
