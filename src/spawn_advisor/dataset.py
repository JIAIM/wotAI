import json
from pathlib import Path

import pandas as pd

from spawn_advisor.replay.battle import find_battle_start, position_at
from spawn_advisor.replay.container import read_replay_file
from spawn_advisor.replay.crypto import decrypt_packet_stream
from spawn_advisor.replay.packets import read_packets
from spawn_advisor.replay.positions import extract_positions

SNAPSHOT_SECONDS = 90
PARSER_VERSION = "v1"   


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
            continue

        result = battle["vehicles"][tank_id][0]
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
            "team": vehicle["team"],
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


def process_replay(path: Path) -> dict:
    """Обрабатывает один реплей.

    Возвращает {"rows": [...], "reason": None}, если всё получилось,
    или {"rows": [], "reason": "почему пропущен"}.
    """
    try:
        rows = build_rows(path)
    except Exception as error:
        return {"rows": [], "reason": str(error)}
    if not rows:
        return {"rows": [], "reason": "нет результатов или старта боя"}
    return {"rows": rows, "reason": None}


def load_or_process(path: Path, cache_dir: Path) -> dict:
    """Результат process_replay для файла: из кэша, если он есть,
    иначе обработать и сохранить в кэш."""
    cache_file = cache_dir / f"{path.parent.name}__{path.stem}.json"

    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    result = process_replay(path)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


def build_dataset(raw_dir: Path, cache_dir: Path) -> pd.DataFrame:
    """Строки по всем реплеям в raw_dir и её подпапках, без дубликатов.

    Каждый реплей обрабатывается один раз: результат хранится в cache_dir.
    Пропущенные файлы с причинами сохраняются в data/processed/skipped.csv.
    """
    paths = sorted(raw_dir.rglob("*.wotreplay"))
    print("найдено файлов:", len(paths))

    all_rows = []
    skipped = []
    for i, path in enumerate(paths, start=1):
        if i % 200 == 0:
            print(f"{i}/{len(paths)}")

        result = load_or_process(path, cache_dir)
        if result["reason"] is not None:
            skipped.append({"file": path.name, "source": path.parent.name, "reason": result["reason"]})
            continue

        rows = result["rows"]
        for row in rows:
            row["source"] = path.parent.name
            row["file"] = path.name
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    before = len(df)
    df = df.drop_duplicates(subset=["arena_id", "tank_id"])

    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(skipped).to_csv(output_dir / "skipped.csv", index=False)

    print("пропущено файлов:", len(skipped))
    print(f"строк: {len(df)}, убрано дубликатов: {before - len(df)}")
    return df


if __name__ == "__main__":
    df = build_dataset(Path("data/raw"), Path("data/interim") / f"parser_{PARSER_VERSION}")
    print(df.shape)
    print(df["map_name"].value_counts().head(10))

    output = Path("data/processed/dataset.parquet")
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output, index=False)
    print("сохранено:", output)