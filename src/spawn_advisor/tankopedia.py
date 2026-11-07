import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

API_URL = "https://api.worldoftanks.eu/wot/encyclopedia/vehicles/"
FIELDS = "tag,name,tier,type,nation,is_premium"
PAGE_LIMIT = 100


def get_application_id() -> str:
    """Ключ API из файла .env или переменной окружения WG_APPLICATION_ID."""
    load_dotenv()
    app_id = os.getenv("WG_APPLICATION_ID")
    if not app_id:
        raise RuntimeError("Нет WG_APPLICATION_ID: добавьте его в файл .env в корне проекта")
    return app_id


def fetch_vehicles(app_id: str) -> list[dict]:
    """Все танки из Tankopedia, постранично."""
    vehicles = []
    page = 1
    while True:
        response = requests.get(API_URL, params={
            "application_id": app_id,
            "fields": FIELDS,
            "limit": PAGE_LIMIT,
            "page_no": page,
        }, timeout=30)
        response.raise_for_status()
        body = response.json()
        if body["status"] != "ok":
            raise RuntimeError(f"Ошибка WG API: {body.get('error')}")

        vehicles.extend(body["data"].values())

        page_total = body["meta"].get("page_total", 1)
        if page >= page_total:
            break
        page += 1
    return vehicles


def to_table(vehicles: list[dict]) -> pd.DataFrame:
    """Таблица танков с ключом vehicle_type в формате датасета: 'nation:tag'."""
    tanks = pd.DataFrame(vehicles)
    tanks["vehicle_type"] = tanks["nation"] + ":" + tanks["tag"]
    return tanks.rename(columns={"type": "tank_class", "name": "tank_name", "tier": "tank_tier"})


if __name__ == "__main__":
    vehicles = fetch_vehicles(get_application_id())
    tanks = to_table(vehicles)
    print(tanks.shape)
    print(tanks["tank_class"].value_counts())

    output = Path("data/processed/tankopedia.parquet")
    output.parent.mkdir(parents=True, exist_ok=True)
    tanks.to_parquet(output, index=False)
    print("сохранено:", output)