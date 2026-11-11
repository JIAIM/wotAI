from pathlib import Path

import pandas as pd

ZONE_SIZE = 100
K = 50              # сглаживание, как в бейзлайне
MIN_COUNT = 10      # зона должна встретиться хотя бы 10 раз
TOP_N = 3
KEYS = ["map_name", "team", "zone"]

MIN_DISTANCE = 200   # метров между советуемыми точками


def pick_spread(zones: pd.DataFrame, n: int = TOP_N, min_distance: float = MIN_DISTANCE) -> pd.DataFrame:
    """Жадно выбирает n лучших зон так, чтобы любые две были дальше min_distance друг от друга."""
    chosen = []
    for _, zone in zones.sort_values("score", ascending=False).iterrows():
        far_enough = all(
            ((zone["center_x"] - c["center_x"]) ** 2 + (zone["center_z"] - c["center_z"]) ** 2) ** 0.5 >= min_distance
            for c in chosen
        )
        if far_enough:
            chosen.append(zone)
        if len(chosen) == n:
            break
    return pd.DataFrame(chosen)


def build_recommendations(features: pd.DataFrame) -> pd.DataFrame:
    """По 3 лучшие зоны для каждой карты и стороны: сглаженная тепловая карта."""
    stats = features.groupby(KEYS).agg(
        zone_x=("zone_x", "first"),
        zone_z=("zone_z", "first"),
        damage_sum=("damage_rel", "sum"),
        count=("damage_rel", "count"),
    ).reset_index()
    stats = stats[stats["count"] >= MIN_COUNT]
    stats["score"] = (stats["damage_sum"] + K) / (stats["count"] + K)

    # центр клетки в метрах: клетка -3 по x — это от -300 до -200, центр -250
    stats["center_x"] = (stats["zone_x"] + 0.5) * ZONE_SIZE
    stats["center_z"] = (stats["zone_z"] + 0.5) * ZONE_SIZE

    parts = [pick_spread(zones) for _, zones in stats.groupby(["map_name", "team"])]
    top = pd.concat(parts, ignore_index=True)
    top["rank"] = top.groupby(["map_name", "team"]).cumcount() + 1
    return top.sort_values(["map_name", "team", "rank"])[
        ["map_name", "team", "rank", "zone", "center_x", "center_z", "score", "count"]
    ]


if __name__ == "__main__":
    processed = Path("data/processed")
    features = pd.read_parquet(processed / "features.parquet")
    recs = build_recommendations(features)
    print(recs.head(12).to_string(index=False))
    print("карт и сторон с советом:", recs.groupby(["map_name", "team"]).ngroups)
    recs.to_parquet(processed / "recommendations.parquet", index=False)
    print("сохранено:", processed / "recommendations.parquet")