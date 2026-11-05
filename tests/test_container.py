from pathlib import Path

import pytest

from spawn_advisor.replay.container import read_replay_file

FIXTURE = Path("tests/fixtures/ensk_final.wotreplay")
MY_TANK_ID = "546159993"  # строка: в JSON ключи всегда строки


@pytest.fixture
def replay():
    return read_replay_file(FIXTURE)


def test_header(replay):
    assert replay.header["mapName"] == "06_ensk"
    assert replay.header["playerName"] == "richGalaxy"
    assert len(replay.header["vehicles"]) == 30


def test_my_damage(replay):
    my_result = replay.results[0]["vehicles"][MY_TANK_ID][0]
    assert my_result["damageDealt"] == 1167


def test_encrypted_size(replay):
    assert len(replay.encrypted) == 1580640


def test_not_a_replay(tmp_path):
    fake = tmp_path / "fake.wotreplay"
    fake.write_bytes(b"\x00" * 100)
    with pytest.raises(ValueError):
        read_replay_file(fake)