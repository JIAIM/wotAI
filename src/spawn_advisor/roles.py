"""Роли танков (штурмовая ПТ, снайперская ПТ, …) из файлов клиента World of Tanks.

Роли лежат в res/packages/scripts.pkg (это zip) в файлах
scripts/item_defs/vehicles/<нация>/list.xml. Эти XML не текстовые, а в «упакованном»
двоичном формате движка BigWorld, поэтому ниже — маленький парсер этого формата.

Запуск из корня проекта:
    python -m spawn_advisor.roles "D:\\Games\\World_of_Tanks_EU\\res\\packages\\scripts.pkg"
Результат: data/processed/roles.parquet с колонками vehicle_type ("нация:тег", как в датасете) и role.
"""
import struct
import sys
import zipfile
from pathlib import Path

import pandas as pd

PACKED_MAGIC = 0x62A14E45
TYPE_ELEMENT, TYPE_STRING = 0, 1
LIST_PREFIX = "scripts/item_defs/vehicles/"
LIST_SUFFIX = "/list.xml"


def read_names(data):
    """Словарь имён тегов: строки, оканчивающиеся нулевым байтом, до пустой строки."""
    pos = 5                                    # 4 байта магии + 1 байт версии
    names = []
    while True:
        end = data.index(b"\0", pos)
        name = data[pos:end].decode("latin1")
        pos = end + 1
        if not name:
            return names, pos
        names.append(name)


def read_element(buf, names):
    """Элемент: число детей, описатель своих данных, описатели детей, потом сами данные.

    Описатель — u32: старшие 4 бита — тип, младшие 28 — где заканчиваются данные.
    """
    n_children = struct.unpack_from("<H", buf, 0)[0]
    own_end = struct.unpack_from("<I", buf, 2)[0] & 0x0FFFFFFF
    children = [struct.unpack_from("<HI", buf, 6 + 6 * i) for i in range(n_children)]
    base = 6 + 6 * n_children

    result = {}
    prev = own_end
    for name_index, descriptor in children:
        kind, end = descriptor >> 28, descriptor & 0x0FFFFFFF
        chunk = buf[base + prev:base + end]
        prev = end
        if kind == TYPE_ELEMENT:
            result[names[name_index]] = read_element(chunk, names)
        elif kind == TYPE_STRING:
            result[names[name_index]] = chunk.decode("latin1")
    return result


def parse_packed_xml(data):
    if struct.unpack_from("<I", data, 0)[0] != PACKED_MAGIC:
        raise ValueError("не упакованный XML BigWorld")
    names, pos = read_names(data)
    return read_element(data[pos:], names)


def vehicle_roles(scripts_pkg):
    """Строки (vehicle_type, role) для всех машин всех наций; role пустая у машин без роли."""
    rows = []
    with zipfile.ZipFile(scripts_pkg) as archive:
        for path in archive.namelist():
            if not (path.startswith(LIST_PREFIX) and path.endswith(LIST_SUFFIX)):
                continue
            nation = path[len(LIST_PREFIX):-len(LIST_SUFFIX)]
            vehicles = parse_packed_xml(archive.read(path))
            for tag, vehicle in vehicles.items():
                tags = vehicle.get("tags", "") if isinstance(vehicle, dict) else ""
                role = next((t for t in tags.split() if t.startswith("role_")), "")
                rows.append({"vehicle_type": f"{nation}:{tag}", "role": role})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    roles = vehicle_roles(sys.argv[1])
    out = Path("data/processed/roles.parquet")
    roles.to_parquet(out, index=False)
    print(len(roles), "машин,", (roles["role"] != "").sum(), "с ролью →", out)
    print(roles["role"].value_counts().to_string())
