import pandas as pd

from spawn_advisor.features import build_features, team_composition

TANKS = pd.DataFrame({
    "vehicle_type": ["a:HT", "a:TD", "a:LT"],
    "tank_name": ["HT", "TD", "LT"],
    "tank_tier": [10, 10, 9],
    "tank_class": ["heavyTank", "AT-SPG", "lightTank"],
})


def roster():
    return pd.DataFrame({
        "arena_id": [1] * 6,
        "team": [1, 1, 1, 2, 2, 2],
        "tank_id": [1, 2, 3, 4, 5, 6],
        "vehicle_type": ["a:HT", "a:TD", "a:LT", "a:HT", "a:TD", "a:TD"],
    })


def player(tank_id, vehicle_type, damage, x, z, alive=True):
    return {"arena_id": 1, "team": 1, "tank_id": tank_id, "vehicle_type": vehicle_type,
            "damage": damage, "x": x, "z": z, "alive_at_90": alive, "battle_type": 1,
            "gameplay_id": "ctf", "is_bot": False, "client_version": "2.4.1"}


def test_team_composition_counts_classes():
    comp = team_composition(roster(), TANKS).set_index("team")
    assert comp.loc[1, ["n_ht", "n_td", "n_lt", "n_mt", "n_spg"]].tolist() == [1, 1, 1, 0, 0]
    assert comp.loc[2, "n_td"] == 2
    assert comp.loc[1, "max_tier"] == 10


def test_damage_rel_uses_all_players_before_filter():
    df = pd.DataFrame([
        player(1, "a:HT", 3000, -150, 250),
        player(2, "a:TD", 1000, 10, 10),
        player(3, "a:LT", 2000, 0, 0, alive=False),   # отфильтруется, но в среднем участвует
    ])
    features = build_features(df, roster(), TANKS).set_index("tank_id")

    assert list(features.index) == [1, 2]
    assert features.loc[1, "damage_rel"] == 1.5          # 3000 / среднее 2000
    assert features.loc[1, "zone"] == "-2_2"             # floor(-1.5) = -2
    assert features.loc[2, "tier_diff"] == 0
    assert features.loc[1, "enemy_n_td"] == 2
