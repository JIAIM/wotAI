import struct
import zlib

from Crypto.Cipher import Blowfish

REPLAY_KEY = bytes.fromhex("DE72BEA0DE04BEB1DEFEBEEFDEADBEEF")
BLOCK_SIZE = 8


def xor_bytes(a: bytes, b: bytes) -> bytes:
    """Побайтовый XOR двух последовательностей одинаковой длины."""
    result = []
    for x,y in zip(a,b):
        result.append(x^y)
    return bytes(result)


def decrypt_packet_stream(encrypted: bytes) -> bytes:
    """Хвост финального реплея → поток пакетов (как в temp.wotreplay)."""
    decompressed_size, compressed_size = struct.unpack('<II', encrypted[:8])
    data = encrypted[8:]
    cipher = Blowfish.new(REPLAY_KEY, Blowfish.MODE_ECB)
    result = bytearray()
    previous = None
    for i in range(0, len(data), BLOCK_SIZE):
        chunk = data[i:i+BLOCK_SIZE]                 
        plain = cipher.decrypt(chunk)               
        if previous is not None:
            plain = xor_bytes(previous, plain)            
        result += plain
        previous = plain
    return zlib.decompress(bytes(result))
    