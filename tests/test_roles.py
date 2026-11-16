import io
import struct
import zipfile

from spawn_advisor.roles import PACKED_MAGIC, parse_packed_xml, vehicle_roles


def element(children):
    """Упакованный элемент BigWorld: [(индекс имени, тип, байты)], своих данных нет."""
    header = struct.pack("<HI", len(children), 0)
    data, end = b"", 0
    for name_index, kind, payload in children:
        end += len(payload)
        header += struct.pack("<HI", name_index, (kind << 28) | end)
        data += payload
    return header + data


def packed_list(vehicles):
    """list.xml из {тег машины: строка tags}."""
    names = list(vehicles) + ["tags"]
    tags_index = len(names) - 1
    root = element([
        (i, 0, element([(tags_index, 1, tags.encode())])) for i, tags in enumerate(vehicles.values())
    ])
    head = struct.pack("<I", PACKED_MAGIC) + b"\0"
    return head + b"".join(n.encode() + b"\0" for n in names) + b"\0" + root


def test_parse_packed_xml():
    parsed = parse_packed_xml(packed_list({"GB83_FV4005": "AT-SPG role_ATSPG_support"}))
    assert parsed == {"GB83_FV4005": {"tags": "AT-SPG role_ATSPG_support"}}


def test_vehicle_roles_from_pkg(tmp_path):
    pkg = tmp_path / "scripts.pkg"
    with zipfile.ZipFile(pkg, "w") as archive:
        archive.writestr("scripts/item_defs/vehicles/uk/list.xml",
                         packed_list({"GB83_FV4005": "AT-SPG role_ATSPG_support", "GB01_Old": "mediumTank"}))
        archive.writestr("scripts/item_defs/vehicles/uk/other.xml", b"ignored")
    roles = vehicle_roles(pkg).set_index("vehicle_type")["role"]
    assert roles.to_dict() == {"uk:GB83_FV4005": "role_ATSPG_support", "uk:GB01_Old": ""}
