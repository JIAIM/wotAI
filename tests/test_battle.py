from pathlib import Path

import pytest

from spawn_advisor.replay.battle import find_battle_start, position_at
from spawn_advisor.replay.packets import read_temp_replay
from spawn_advisor.replay.positions import extract_positions

MY_TANK_ID = 9227663


@pytest.fixture
def packets():
    return read_temp_replay(Path("tests/fixtures/temp.wotreplay"))


def test_battle_start(packets):
    assert find_battle_start(packets) == pytest.approx(29.42, abs=0.01)


def test_my_position_at_90s(packets):
    start = find_battle_start(packets)
    positions = extract_positions(packets)
    pos = position_at(positions, MY_TANK_ID, start + 90)
    assert pos.x == pytest.approx(21.34, abs=0.01)
    assert pos.z == pytest.approx(-42.57, abs=0.01)


def test_unknown_tank():
    assert position_at([], 12345, 100.0) is None