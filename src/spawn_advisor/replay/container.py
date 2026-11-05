import json
import struct
from dataclasses import dataclass
from pathlib import Path

REPLAY_MAGIC = 0x11343212


@dataclass
class ReplayFile:
    header: dict              # блок 0
    results: list | None      # блок 1, None если игрок вышел до конца боя
    encrypted: bytes          # всё после блоков, для расшифровки в 4б


def read_replay_file(path: Path) -> ReplayFile:
    """Читает финальный .wotreplay: JSON-блоки и зашифрованный хвост."""
    data = path.read_bytes()
    magic, block_count = struct.unpack('<II', data[:8])
    if magic != REPLAY_MAGIC:
        raise ValueError("не реплей WoT")
    offset = 8          # первые 8 байт уже прочитаны: magic и block_count
    blocks = []
    for _ in range(block_count):
        block_size, = struct.unpack('<I', data[offset:offset + 4])
        offset += 4
        block = data[offset:offset + block_size]
        offset += block_size
        blocks.append(json.loads(block))
    
    return ReplayFile(header = blocks[0], results = blocks[1] if len(blocks)>1 else None, encrypted = data[offset:])
    
       