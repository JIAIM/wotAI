import re
from pathlib import Path

import pandas as pd

from spawn_advisor.replay.packets import Packet
from spawn_advisor.replay.positions import extract_positions

MAP_PACKET_TYPE = 15
EARLY_SECONDS = 10


def read_map_name(packets: list[Packet]) -> str | None:
    """Название карты из пакета типа 15: 'spaces/05_prohorovka' → '05_prohorovka'."""
    for packet in packets:
        if packet.type == MAP_PACKET_TYPE:
            match = re.search(rb"spaces/(\w+)", packet.payload)
            if match:
                return match.group(1).decode()
    return None


def team_centers(features: pd.DataFrame) -> pd.DataFrame:
    """Средняя позиция на 90-й секунде для каждой карты и стороны."""
    return features.groupby(["map_name", "team"])[["x", "z"]].mean().reset_index()


def detect_team(packets: list[Packet], map_name: str, centers: pd.DataFrame) -> int | None:
    """Сторона игрока: центр позиций в первые секунды — это союзники; к чьему центру он ближе."""
    positions = extract_positions(packets)
    if not positions:
        return None
    start = positions[0].time
    early = [p for p in positions if p.time <= start + EARLY_SECONDS]
    cx = sum(p.x for p in early) / len(early)
    cz = sum(p.z for p in early) / len(early)

    map_centers = centers[centers["map_name"] == map_name]
    if len(map_centers) != 2:
        return None
    distances = ((map_centers["x"] - cx) ** 2 + (map_centers["z"] - cz) ** 2) ** 0.5
    return int(map_centers.loc[distances.idxmin(), "team"])

if __name__ == "__main__":
    import random
    from spawn_advisor.replay.container import read_replay_file
    from spawn_advisor.replay.crypto import decrypt_packet_stream
    from spawn_advisor.replay.packets import read_packets

    features = pd.read_parquet("data/processed/features.parquet")
    centers = team_centers(features)

    paths = sorted(Path("data/raw").rglob("*.wotreplay"))
    random.seed(0)
    sample = random.sample(paths, 200)

    correct = total = 0
    for path in sample:
        try:
            replay = read_replay_file(path)
        except ValueError:
            continue
        if replay.results is None or replay.header.get("gameplayID") != "ctf":
            continue
        header = replay.header
        true_team = next(v["team"] for v in header["vehicles"].values() if v["name"] == header["playerName"])
        packets = read_packets(decrypt_packet_stream(replay.encrypted))
        map_name = read_map_name(packets)
        guess = detect_team(packets, map_name, centers)
        if guess is None:
            continue
        total += 1
        correct += guess == true_team
    print(f"сторона угадана: {correct} из {total} ({correct / total:.1%})")