from pathlib import Path

import numpy as np
import pandas as pd

ZONE_SIZE = 100
CLASSES = ["lightTank", "mediumTank", "heavyTank", "AT-SPG", "SPG"]
SHORT = {"lightTank": "lt", "mediumTank": "mt", "heavyTank": "ht", "AT-SPG": "td", "SPG": "spg"}


def team_composition(roster: pd.DataFrame, tanks: pd.DataFrame) -> pd.DataFrame:
    """По строке на (бой, команда): число танков каждого класса, средний и максимальный уровень."""
    r = roster.merge(tanks[["vehicle_type", "tank_name", "tank_tier", "tank_class"]],on="vehicle_type", how="left")
    counts = r.pivot_table(
        index=["arena_id","team"],       # строки: пара «бой, команда» — два названия колонок
        columns="tank_class",     # колонки: класс танка
        values="tank_id",      # что считаем: колонка, которая есть у каждого танка, например tank_id
        aggfunc="count",
        fill_value=0,
    )
    counts = counts.reindex(columns=CLASSES, fill_value=0)
    counts = counts.rename(columns=lambda c: f"n_{SHORT[c]}")
    
    tiers = r.groupby(["arena_id","team"])["tank_tier"].agg(avg_tier="mean", max_tier="max")
    return counts.join(tiers).reset_index()
    

def build_features(df: pd.DataFrame, roster: pd.DataFrame, tanks: pd.DataFrame) -> pd.DataFrame:
    """Таблица для модели: стандартный бой, живые люди с известной позицией."""
    # TODO шаг 3


if __name__ == "__main__":
    processed = Path("data/processed")
    df = pd.read_parquet(processed / "dataset.parquet")
    roster = pd.read_parquet(processed / "roster.parquet")
    tankopedia = pd.read_parquet(processed / "tankopedia.parquet")
    print(df.shape, roster.shape, tankopedia.shape)
    team_composition(roster=roster,tanks=tankopedia)
    comp = team_composition(roster, tankopedia)
    print(comp.shape)
    print(comp.head())