from dataclasses import dataclass
from pathlib import Path
import struct


@dataclass
class Packet:
    type: int      # тип пакета
    time: float    # время от начала записи, секунды
    payload: bytes # данные пакета


def read_packets(data: bytes) -> list[Packet]:
    """Разбирает поток пакетов.

    Каждый пакет: [размер uint32][тип uint32][время float32][данные: размер байт].
    Все числа little-endian. Если последний пакет обрезан, его пропускаем.
    """
    offset = 0
    packets = []
    
    while offset + 12<=len(data):
        header = data[offset:offset+12]  # первые 12 байт из data (срез)
        offset += 12
        size, packet_type, time = struct.unpack('<IIf', header)  # struct.unpack с форматом '<IIf'
        if offset + size > len(data):
            break
        payload = data[offset:offset+size]
        packet = Packet(type=packet_type, time=time, payload=payload)
        packets.append(packet)
        offset += size
        
    return packets
    

def read_temp_replay(path: Path) -> list[Packet]:
    """temp.wotreplay — это сразу поток пакетов, без заголовка."""
    with open(path, mode='rb') as file: 
        data = file.read()
    return read_packets(data)
    