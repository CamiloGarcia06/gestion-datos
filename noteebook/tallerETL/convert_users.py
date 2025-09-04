#!/usr/bin/env python3
"""
Convert users from JSON to CSV, JSON (flattened) and XML.

Input:
  - /home/camilo-arch/gestion-datos/noteebook/taller2/data/users.json

Outputs (written beside this script):
  - users.csv
  - users.json (nested with selected fields only: id, name, username, email, phone, website, address{...}, company{...})
  - users.xml (nested structure)
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List
import xml.etree.ElementTree as ET


WORKSPACE_DIR = Path("/home/camilo-arch/gestion-datos")
SCRIPT_DIR = WORKSPACE_DIR / "noteebook" / "taller2"
SOURCE_JSON = SCRIPT_DIR / "data" / "users.json"

DEST_CSV = SCRIPT_DIR / "users.csv"
DEST_JSON = SCRIPT_DIR / "users.json"
DEST_XML = SCRIPT_DIR / "users.xml"


def load_users(path: Path) -> List[Dict[str, Any]]:
    """Load users from the given JSON file.

    Accepts either a dict with key "users" or a raw list of users.
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "users" in data:
        records = data["users"]
    elif isinstance(data, list):
        records = data
    else:
        raise ValueError("Formato de JSON no esperado: debe ser lista o contener clave 'users'.")
    if not isinstance(records, list):
        raise ValueError("La clave 'users' debe contener una lista de usuarios.")
    return records  # type: ignore[return-value]


def flatten(prefix: str, obj: Any, out: Dict[str, Any]) -> None:
    """Recursively flattens a nested dict/list structure into dot-notated keys.

    Examples:
      address.street -> "Kulas Light"
      address.geo.lat -> "-37.3159"
    Lists are indexed: items.0, items.1, ... (not used in current dataset but supported).
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_prefix = f"{prefix}.{key}" if prefix else key
            flatten(new_prefix, value, out)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            new_prefix = f"{prefix}.{index}" if prefix else str(index)
            flatten(new_prefix, value, out)
    else:
        out[prefix] = obj


def flatten_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    for record in records:
        flat: Dict[str, Any] = {}
        flatten("", record, flat)
        flattened.append(flat)
    return flattened


def select_user_fields(user: Dict[str, Any]) -> Dict[str, Any]:
    """Return only the requested fields in the specified nested structure.

    Structure:
    {
      id, name, username, email, phone, website,
      address: { street, suite, city, zipcode, geo: { lat, lng } },
      company: { name, catchPhrase, bs }
    }
    """
    address = user.get("address", {}) or {}
    geo = address.get("geo", {}) or {}
    company = user.get("company", {}) or {}
    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "username": user.get("username"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "website": user.get("website"),
        "address": {
            "street": address.get("street"),
            "suite": address.get("suite"),
            "city": address.get("city"),
            "zipcode": address.get("zipcode"),
            "geo": {
                "lat": geo.get("lat"),
                "lng": geo.get("lng"),
            },
        },
        "company": {
            "name": company.get("name"),
            "catchPhrase": company.get("catchPhrase"),
            "bs": company.get("bs"),
        },
    }


def write_csv(records: List[Dict[str, Any]], dest_path: Path) -> None:
    # Collect header keys across all records to ensure a stable set of columns
    header_keys: List[str] = sorted({key for rec in records for key in rec.keys()})
    with dest_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header_keys)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)


def dict_to_xml_element(tag: str, value: Any) -> ET.Element:
    """Convert a Python value to an XML element with the given tag.

    - dict -> nested elements with keys as tags
    - list -> repeated <item> children
    - primitives -> text content
    """
    elem = ET.Element(tag)
    if isinstance(value, dict):
        for k, v in value.items():
            child = dict_to_xml_element(k, v)
            elem.append(child)
    elif isinstance(value, list):
        for item in value:
            child = dict_to_xml_element("item", item)
            elem.append(child)
    else:
        # Convert to string for XML text
        elem.text = "" if value is None else str(value)
    return elem


def users_to_xml(users: List[Dict[str, Any]]) -> ET.ElementTree:
    root = ET.Element("users")
    for user in users:
        user_elem = dict_to_xml_element("user", user)
        root.append(user_elem)
    return ET.ElementTree(root)


def pretty_print_xml(element: ET.Element) -> str:
    """Return a pretty-printed XML string for the Element.

    Uses xml.etree only (no extra dependencies)."""
    # Minimal pretty-print: manual indentation
    def indent(elem: ET.Element, level: int = 0) -> None:
        indent_str = "  "
        i = "\n" + level * indent_str
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + indent_str
            for child in elem:
                indent(child, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    indent(element)
    return ET.tostring(element, encoding="unicode")


def main() -> None:
    os.makedirs(SCRIPT_DIR, exist_ok=True)
    users = load_users(SOURCE_JSON)

    # Flattened for CSV and JSON
    flattened_users = flatten_records(users)

    # CSV
    write_csv(flattened_users, DEST_CSV)

    # JSON (nested with only requested fields)
    selected_users = [select_user_fields(u) for u in users]
    with DEST_JSON.open("w", encoding="utf-8") as jf:
        json.dump(selected_users, jf, ensure_ascii=False, indent=2)

    # XML (nested structure akin to original per-user dict)
    tree = users_to_xml(users)
    # Pretty print and write
    xml_string = pretty_print_xml(tree.getroot())
    with DEST_XML.open("w", encoding="utf-8") as xf:
        xf.write(xml_string)

    print(f"Escritura completada:\n - {DEST_CSV}\n - {DEST_JSON}\n - {DEST_XML}")


if __name__ == "__main__":
    main()
