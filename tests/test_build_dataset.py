import shutil
from pathlib import Path

from spawn_advisor.dataset import build_dataset

FIXTURES = Path("tests/fixtures")


def test_build_dataset(tmp_path):
    # мои реплеи
    (tmp_path / "mine").mkdir()
    shutil.copy(FIXTURES / "ensk_final.wotreplay", tmp_path / "mine")
    shutil.copy(FIXTURES / "temp.wotreplay", tmp_path / "mine")   # не финальный — должен быть пропущен

    # реплеи друга, один бой совпадает с моим (как будто играли во взводе)
    (tmp_path / "friend").mkdir()
    shutil.copy(FIXTURES / "westfeld_240.wotreplay", tmp_path / "friend")
    shutil.copy(FIXTURES / "ensk_final.wotreplay", tmp_path / "friend" / "copy.wotreplay")

    df = build_dataset(tmp_path, tmp_path / "cache")

    assert len(df) == 30                       # 15 + 15, дубликат убран
    assert df["arena_id"].nunique() == 2
    assert (df["map_name"] == "06_ensk").sum() == 15          # Энск ровно один раз, а не дважды
    assert set(df.loc[df["map_name"] == "23_westfeld", "source"]) == {"friend"}
    
def test_cache(tmp_path):
    raw = tmp_path / "raw" / "mine"
    raw.mkdir(parents=True)
    shutil.copy(FIXTURES / "ensk_final.wotreplay", raw)
    shutil.copy(FIXTURES / "temp.wotreplay", raw)
    cache = tmp_path / "cache"

    first = build_dataset(tmp_path / "raw", cache)
    assert len(list(cache.glob("*.json"))) == 2     # кэш и для хорошего, и для пропущенного файла

    second = build_dataset(tmp_path / "raw", cache)
    assert len(second) == len(first) == 15