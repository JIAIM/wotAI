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

        # БЫЛО: распаковка method_id и проверка «!= ARENA_METHOD_ID» — удалить обе строки.
        # СТАЛО: проверка длины, как в детекторе:
        if len(packet.payload) < 15:
            continue

        if packet.payload[12] != PERIOD_SUB_ID:
            continue

        # БЫЛО: разжатие и распаковка без защиты.
        # СТАЛО: то же самое внутри try, потому что теперь сюда доходят
        # пакеты любых методов, и многие из них не zlib и не pickle:
        try:
            raw = zlib.decompress(packet.payload[14:])
            period_info = SafeUnpickler(io.BytesIO(raw)).load()
        except Exception:
            continue

        # БЫЛО: if period_info[0] == BATTLE_PERIOD
        # СТАЛО: строже — проверяем форму кортежа целиком:
        if isinstance(period_info, tuple) and len(period_info) == 4 and period_info[0] == BATTLE_PERIOD:
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
    