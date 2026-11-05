import io
import pickle
import struct
import zlib

from spawn_advisor.replay.packets import Packet
from spawn_advisor.replay.positions import Position

METHOD_CALL_PACKET_TYPE = 8
ARENA_METHOD_ID = 58
PERIOD_SUB_ID = 3
BATTLE_PERIOD = 3


class SafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        raise pickle.UnpicklingError(f"запрещено: {module}.{name}")


def find_battle_start(packets: list[Packet]) -> float | None:
    """Время записи (в секундах), когда начался бой (период 3).

    None, если бой ещё не начался (например, temp-файл скопирован на загрузке).
    """
    for packet in packets:
        if packet.type != METHOD_CALL_PACKET_TYPE:
            continue
        method_id, = struct.unpack('<I', packet.payload[4:8])         
        if method_id != ARENA_METHOD_ID:
            continue
        if packet.payload[12] != PERIOD_SUB_ID :               
            continue
        compressed = packet.payload[14:]
        raw = zlib.decompress(compressed)
        period_info = SafeUnpickler(io.BytesIO(raw)).load()
        
        if period_info[0] == BATTLE_PERIOD:
            return packet.time     
    return None
            

def position_at(positions: list[Position], entity_id: int, time: float) -> Position | None:
    """Последняя известная позиция танка на момент time (включительно).

    None, если до этого момента танк ни разу не был виден.
    """
    result = None
    for position in positions:
        if position.entity_id != entity_id:
            continue
        if position.time > time:
            break
        result = position
    return result
    
if __name__ == "__main__":
    from pathlib import Path
    from spawn_advisor.replay.packets import read_temp_replay

    packets = read_temp_replay(Path("tests/fixtures/temp.wotreplay"))
    print(find_battle_start(packets))
    
    from spawn_advisor.replay.positions import extract_positions

    start = find_battle_start(packets)
    positions = extract_positions(packets)
    print(position_at(positions, 9227663, start + 90))