import re
import os
import time
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt   

from spawn_advisor.replay.packets import Packet
from spawn_advisor.replay.positions import extract_positions

MAP_PACKET_TYPE = 15
EARLY_SECONDS = 10
POLL_SECONDS = 2
COLORS = {1: "darkviolet", 2: "turquoise", 3: "limegreen"}   # к константам в начале файла


def watch(replays_dir: Path, features: pd.DataFrame, recs: pd.DataFrame, output: Path) -> None:
    """Следит за temp.wotreplay и показывает совет один раз на каждый новый бой."""
    centers = team_centers(features)
    temp = replays_dir / "temp.wotreplay"
    done_battle = None   # время создания temp-файла, для которого совет уже показан

    print(f"Слежу за {temp}. Остановить — Ctrl+C.")
    while True:
        time.sleep(POLL_SECONDS)
        if not temp.exists():
            continue
        battle = temp.stat().st_ctime
        if battle == done_battle:
            continue

        try:
            packets = read_temp_replay(temp)
        except (OSError, ValueError):
            continue        # игра как раз пишет файл — попробуем через 2 секунды
        map_name = read_map_name(packets)
        if map_name is None:
            continue
        team = detect_team(packets, map_name, centers)
        if team is None:
            continue

        if recs[(recs["map_name"] == map_name) & (recs["team"] == team)].empty:
            print(f"{map_name}, сторона {team}: для этой карты пока мало данных")
        else:
            plot_advice(features, recs, map_name, team, output)
            print(f"{map_name}, сторона {team}: совет готов")
            os.startfile(output)     # открыть картинку программой по умолчанию (Windows)
        done_battle = battle

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

def plot_advice(features: pd.DataFrame, recs: pd.DataFrame, map_name: str, team: int, output: Path) -> None:
    """Силуэт карты из всех позиций + 3 советуемые точки. Сохраняет PNG."""
    background = features[features["map_name"] == map_name]
    advice = recs[(recs["map_name"] == map_name) & (recs["team"] == team)]

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(background["x"], background["z"], s=2, c="lightgray", alpha=0.4)

    for _, zone in advice.iterrows():
        ax.scatter(zone["center_x"], zone["center_z"], s=600, c=COLORS[zone["rank"]], alpha=0.85, edgecolors="black")
        ax.text(zone["center_x"], zone["center_z"], str(zone["rank"]),
                ha="center", va="center", fontsize=16, fontweight="bold", color="white")
        ax.text(zone["center_x"] + 40, zone["center_z"] + 40,
                f"×{zone['score']:.2f} ({zone['count']} танков)", fontsize=9)

    ax.set_xlim(-500, 500)
    ax.set_ylim(-500, 500)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"{map_name}, сторона {team}: куда ехать к 90-й секунде")
    fig.savefig(output, dpi=100, bbox_inches="tight")
    plt.close(fig)

if __name__ == "__main__":
    import sys
    from spawn_advisor.replay.packets import read_temp_replay

    processed = Path("data/processed")
    features = pd.read_parquet(processed / "features.parquet")
    recs = pd.read_parquet(processed / "recommendations.parquet")

    replays_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Games\World_of_Tanks_EU\replays")
    watch(replays_dir, features, recs, Path("advice.png"))