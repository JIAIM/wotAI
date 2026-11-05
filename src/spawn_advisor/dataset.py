import pandas as pd
from pathlib import Path

from spawn_advisor.replay.battle import find_battle_start, position_at
from spawn_advisor.replay.container import read_replay_file
from spawn_advisor.replay.crypto import decrypt_packet_stream
from spawn_advisor.replay.packets import read_packets
from spawn_advisor.replay.positions import extract_positions

SNAPSHOT_SECONDS = 90

    
def build_rows(path: Path) -> list[dict]:
    """Строки датасета по одному финальному реплею: по строке на каждый танк
    команды игрока, записавшего реплей.
    
    Возвращает пустой список, если реплей нельзя использовать
    (нет результатов или не найден старт боя).
    """
    replay = read_replay_file(path)
    if replay.results is None:   
        return []

    stream = decrypt_packet_stream(replay.encrypted)   
    packets = read_packets(stream)       
    battle_start = find_battle_start(packets)   
    if battle_start is None:
        return []
    positions = extract_positions(packets)      

    header = replay.header
    battle = replay.results[0]          

    client_version = header["clientVersionFromExe"]       
    map_name = header["mapName"]
    arena_id = battle["arenaUniqueID"]
    winner_team = battle["common"]["winnerTeam"]
    
    recorder_team = None
    for vehicle in header["vehicles"].values():
        if vehicle["name"] == header["playerName"]:
            recorder_team = vehicle["team"]

    rows = []
    for tank_id, vehicle in header["vehicles"].items():
        if vehicle["team"] != recorder_team:
            continue                                  # враги нам не нужны

        result = battle["vehicles"][tank_id][0]       # результаты этого танка
        position = position_at(positions, int(tank_id), battle_start + SNAPSHOT_SECONDS)

        rows.append({
            "arena_id": arena_id,
            "client_version": client_version,
            "map_name": map_name,
            "battle_type": header["battleType"],
            "gameplay_id": header["gameplayID"],
            "tank_id": int(tank_id),
            "player_name": vehicle["name"],
            "vehicle_type": vehicle["vehicleType"],
            "is_bot": vehicle["name"].startswith(":"),
            "is_recorder": vehicle["name"] == header["playerName"],
            "won": vehicle["team"] == winner_team,
            "x": position.x if position else None,
            "z": position.z if position else None,
            "alive_at_90": result["lifeTime"] >= SNAPSHOT_SECONDS,
            "damage": result["damageDealt"],
            "assist_radio": result["damageAssistedRadio"],
            "spotted": result["spotted"],
            "kills": result["kills"],
            "life_time": result["lifeTime"],
        })

    return rows
    
def build_dataset(raw_dir: Path) -> pd.DataFrame:
    """Строки по всем реплеям в raw_dir и её подпапках, без дубликатов."""
    paths = sorted(raw_dir.rglob("*.wotreplay"))
    print("найдено файлов:", len(paths))
    all_rows = []
    for i, path in enumerate(paths, start=1):
        if i % 50 == 0:
            print(f"{i}/{len(paths)}")
        try:
            rows = build_rows(path)
        except Exception as error:
            print(f"пропущен {path.name}: {error}")
            continue
        if not rows:
            print(f"пропущен {path.name}: нет результатов или старта боя")
            continue
        for row in rows:
            row["source"] = path.parent.name
            row["file"] = path.name
        all_rows.extend(rows)
    df = pd.DataFrame(all_rows)
    before = len(df)
    df = df.drop_duplicates(subset=["arena_id", "tank_id"])
    print(f"строк: {len(df)}, убрано дубликатов: {before - len(df)}")
    return df
    
if __name__ == "__main__":
    df = build_dataset(Path("data/raw"))
    print(df.shape)
    print(df["map_name"].value_counts().head(10))

    output = Path("data/processed/dataset.parquet")
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output, index=False)
    print("сохранено:", output)