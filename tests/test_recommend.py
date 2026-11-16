import pandas as pd

from spawn_advisor.recommend import MIN_COUNT, build_recommendations, pick_spread


def rows(map_name, team, x, z, damage_rel, n):
    zone_x, zone_z = int(x // 100), int(z // 100)
    return [{"map_name": map_name, "team": team, "zone": f"{zone_x}_{zone_z}",
             "zone_x": zone_x, "zone_z": zone_z, "damage_rel": damage_rel}] * n


def test_pick_spread_skips_close_zones():
    zones = pd.DataFrame({
        "center_x": [0, 50, 300, 600],
        "center_z": [0, 0, 0, 0],
        "score": [1.5, 1.4, 1.3, 1.2],
    })
    chosen = pick_spread(zones, n=3, min_distance=200)
    # зона в 50 м от лучшей пропущена
    assert list(chosen["center_x"]) == [0, 300, 600]


def test_build_recommendations_top3_per_side():
    data = (rows("m", 1, 50, 50, 2.0, 30) + rows("m", 1, 450, 50, 1.5, 30)
            + rows("m", 1, 850, 50, 1.2, 30) + rows("m", 1, 850, 850, 0.5, 30)
            + rows("m", 2, -350, -350, 1.8, 30))
    recs = build_recommendations(pd.DataFrame(data))

    side1 = recs[recs["team"] == 1]
    assert list(side1["rank"]) == [1, 2, 3]
    assert list(side1["zone"]) == ["0_0", "4_0", "8_0"]          # худшая зона не попала
    assert side1["score"].is_monotonic_decreasing
    # центр клетки: клетка -4 — это от -400 до -300 м, центр -350
    side2 = recs[recs["team"] == 2].iloc[0]
    assert (side2["center_x"], side2["center_z"]) == (-350.0, -350.0)


def test_rare_zone_is_ignored():
    data = rows("m", 1, 50, 50, 1.1, 30) + rows("m", 1, 550, 50, 5.0, MIN_COUNT - 1)
    recs = build_recommendations(pd.DataFrame(data))
    assert list(recs["zone"]) == ["0_0"]
