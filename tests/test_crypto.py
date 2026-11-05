from pathlib import Path

import pytest

from spawn_advisor.replay.battle import find_battle_start, position_at
from spawn_advisor.replay.container import read_replay_file
from spawn_advisor.replay.crypto import decrypt_packet_stream, xor_bytes
from spawn_advisor.replay.packets import read_packets
from spawn_advisor.replay.positions import extract_positions

FIXTURE = Path("tests/fixtures/ensk_final.wotreplay")
MY_TANK_ID = 546159993


def test_xor_bytes():
    assert xor_bytes(b"\x0c\xff", b"\x0a\x0f") == b"\x06\xf0"


@pytest.fixture
def packets():
    replay = read_replay_file(FIXTURE)
    return read_packets(decrypt_packet_stream(replay.encrypted))


def test_packet_count(packets):
    assert len(packets) == 129373


def test_battle_start(packets):
    assert find_battle_start(packets) == pytest.approx(28.51, abs=0.01)


def test_my_position_at_90s(packets):
    start = find_battle_start(packets)
    pos = position_at(extract_positions(packets), MY_TANK_ID, start + 90)
    assert pos.x == pytest.approx(-242.63, abs=0.01)
    assert pos.z == pytest.approx(121.82, abs=0.01)