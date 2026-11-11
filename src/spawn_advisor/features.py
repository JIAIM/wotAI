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
    df = df.copy()
    df["damage_rel"] = df["damage"] / df.groupby("arena_id")["damage"].transform("mean")
    
    data = df[
        (df["battle_type"] == 1)
        & (df["gameplay_id"] == "ctf")
        & (~df["is_bot"])
        & (df["alive_at_90"])
        & (df["x"].notna())
        & (df["client_version"].str.startswith("2."))
    ].copy()
     
    data = data.merge(tanks[["vehicle_type", "tank_name", "tank_tier", "tank_class"]],on="vehicle_type", how="inner")
    comp = team_composition(roster, tanks)
    ally = comp.add_prefix("ally_").rename(columns={"ally_arena_id": "arena_id", "ally_team": "team"})
    enemy = comp.add_prefix("enemy_").rename(columns={"enemy_arena_id": "arena_id"})
    data["enemy_team"] = 3 - data["team"]
    data = data.merge(ally, on=["arena_id", "team"], how="left")
    data = data.merge(enemy, on=["arena_id", "enemy_team"], how="left")
    battle_max = np.maximum(data["ally_max_tier"], data["enemy_max_tier"])
    data["tier_diff"] = data["tank_tier"] - battle_max
    data["zone_x"] = np.floor(data["x"]/ZONE_SIZE).astype(int)
    data["zone_z"] = np.floor(data["z"]/ZONE_SIZE).astype(int)
    data["zone"] = data["zone_x"].astype(str) + "_" + data["zone_z"].astype(str)
    
    return data
    
if __name__ == "__main__":
    processed = Path("data/processed")
    df = pd.read_parquet(processed / "dataset.parquet")
    roster = pd.read_parquet(processed / "roster.parquet")
    tankopedia = pd.read_parquet(processed / "tankopedia.parquet")
    print(df.shape, roster.shape, tankopedia.shape)
    features = build_features(df, roster, tankopedia)
    print(features.shape)
    print(features[["tank_class", "tank_tier", "tier_diff", "x", "z", "zone", "damage_rel"]].head())
    print("пустых значений:", features.isna().sum().sum())

    same = (features[["ally_n_lt", "ally_n_mt", "ally_n_ht", "ally_n_td", "ally_n_spg"]].values
            == features[["enemy_n_lt", "enemy_n_mt", "enemy_n_ht", "enemy_n_td", "enemy_n_spg"]].values).all(axis=1)
    print("доля строк с одинаковым составом по классам:", same.mean())
    features.to_parquet(processed / "features.parquet", index=False)
    print("сохранено:", processed / "features.parquet")