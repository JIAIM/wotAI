from pathlib import Path

import pytest

from spawn_advisor.dataset import build_rows

FIXTURE = Path("tests/fixtures/ensk_final.wotreplay")


@pytest.fixture(scope="module")
def rows():
    return build_rows(FIXTURE)


def test_row_count(rows):
    assert len(rows) == 15


def test_my_row(rows):
    me = next(r for r in rows if r["is_recorder"])
    assert me["player_name"] == "richGalaxy"
    assert me["vehicle_type"] == "usa:A19_T2_lt"
    assert me["damage"] == 1167
    assert me["won"] is True
    assert me["x"] == pytest.approx(-242.6, abs=0.1)
    assert me["z"] == pytest.approx(121.8, abs=0.1)


def test_bots(rows):
    assert sum(r["is_bot"] for r in rows) == 5


def test_alive_at_90(rows):
    assert sum(r["alive_at_90"] for r in rows) == 13


def test_same_battle(rows):
    assert len({r["arena_id"] for r in rows}) == 1
    assert all(r["map_name"] == "06_ensk" for r in rows)
    assert all(r["client_version"] == "2.4.1.0" for r in rows)
    
FIXTURE_240 = Path("tests/fixtures/westfeld_240.wotreplay")


def test_version_240():
    rows = build_rows(FIXTURE_240)
    assert len(rows) == 15
    assert all(r["client_version"] == "2.4.0.0" for r in rows)
    assert all(r["x"] is not None for r in rows)

    friend = next(r for r in rows if r["is_recorder"])
    assert friend["vehicle_type"] == "japan:J41_Type_68"
    assert friend["damage"] == 4173
    assert friend["won"] is True