from pathlib import Path

import pytest

from spawn_advisor.replay.packets import read_temp_replay
from spawn_advisor.replay.positions import extract_positions

MY_TANK_ID = 9227663  # ваш танк в этом бою


@pytest.fixture
def positions():
    packets = read_temp_replay(Path("tests/fixtures/temp.wotreplay"))
    return extract_positions(packets)


def test_position_count(positions):
    assert len(positions) == 33824


def test_tanks_seen(positions):
    tank_ids = {p.entity_id for p in positions}
    assert len(tank_ids) == 29


def test_my_spawn(positions):
    first = next(p for p in positions if p.entity_id == MY_TANK_ID)
    assert first.x == pytest.approx(6.59, abs=0.01)
    assert first.z == pytest.approx(422.66, abs=0.01)