from pathlib import Path
from spawn_advisor.replay.packets import read_temp_replay

def test_first_packet_is_version():
    packets = read_temp_replay(Path("tests/fixtures/temp.wotreplay"))
    assert packets[0].type == 24
    assert b"2.4.1.0" in packets[0].payload

def test_map_name():
    packets = read_temp_replay(Path("tests/fixtures/temp.wotreplay"))
    map_packet = next(p for p in packets if p.type == 15)
    assert b"19_monastery" in map_packet.payload
    
def test_packet_count():
    packets = read_temp_replay(Path("tests/fixtures/temp.wotreplay"))
    assert len(packets) == 72718