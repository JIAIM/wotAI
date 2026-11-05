import struct

from dataclasses import dataclass
from spawn_advisor.replay.packets import Packet



POSITION_PACKET_TYPE = 10


@dataclass
class Position:
    entity_id: int
    time: float
    x: float
    height: float
    z: float


def parse_position(packet: Packet) -> Position | None:
    """Достаёт позицию из одного пакета типа 10.

    Возвращает None, если объект прикреплён к другому (parent_id != 0).
    """
    entity_id, parent_id = struct.unpack('<II', packet.payload[:8])
    x, height, z = struct.unpack('<fff', packet.payload[8:20])
    
    if parent_id != 0:
        return None
    
    return Position(entity_id=entity_id, time=packet.time, x=x, height=height, z=z)
    
    


def extract_positions(packets: list[Packet]) -> list[Position]:
    """Все позиции из списка пакетов, только пакеты типа 10 с parent_id == 0."""
    positions = []
    for packet in packets:
        if packet.type != POSITION_PACKET_TYPE:
            continue
        
        position = parse_position(packet)
        if position is not None:
            positions.append(position)
            
    return positions
    