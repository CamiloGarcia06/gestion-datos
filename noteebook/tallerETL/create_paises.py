#!/usr/bin/env python3
"""
Crear un dataset de países europeos y exportarlo a CSV, JSON y XML
en versiones legibles e igualmente compactas (minificadas).

Salidas (junto a este script):
  - paises.csv (con encabezado)
  - paises.min.csv (sin encabezado)
  - paises.json (indentado)
  - paises.min.json (compacto)
  - paises.xml (indentado)
  - paises.min.xml (compacto)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List
import xml.etree.ElementTree as ET


SCRIPT_DIR = Path(__file__).resolve().parent


def build_dataset() -> List[Dict[str, Any]]:
    """Construye el dataset con al menos 10 países.

    Campos: "Nombre" (inglés), "Nombre_es", "Nombre_de", "Capital", "Población".
    """
    dataset: List[Dict[str, Any]] = [
        {"Nombre": "Spain", "Nombre_es": "España", "Nombre_de": "Spanien", "Capital": "Madrid", "Población": 47351567},
        {"Nombre": "Germany", "Nombre_es": "Alemania", "Nombre_de": "Deutschland", "Capital": "Berlin", "Población": 83240525},
        {"Nombre": "France", "Nombre_es": "Francia", "Nombre_de": "Frankreich", "Capital": "Paris", "Población": 68042591},
        {"Nombre": "Italy", "Nombre_es": "Italia", "Nombre_de": "Italien", "Capital": "Rome", "Población": 58853482},
        {"Nombre": "Portugal", "Nombre_es": "Portugal", "Nombre_de": "Portugal", "Capital": "Lisbon", "Población": 10305564},
        {"Nombre": "Netherlands", "Nombre_es": "Países Bajos", "Nombre_de": "Niederlande", "Capital": "Amsterdam", "Población": 17533405},
        {"Nombre": "Belgium", "Nombre_es": "Bélgica", "Nombre_de": "Belgien", "Capital": "Brussels", "Población": 11668278},
        {"Nombre": "Austria", "Nombre_es": "Austria", "Nombre_de": "Österreich", "Capital": "Vienna", "Población": 9043072},
        {"Nombre": "Switzerland", "Nombre_es": "Suiza", "Nombre_de": "Schweiz", "Capital": "Bern", "Población": 8740000},
        {"Nombre": "Poland", "Nombre_es": "Polonia", "Nombre_de": "Polen", "Capital": "Warsaw", "Población": 37950802},
        {"Nombre": "Sweden", "Nombre_es": "Suecia", "Nombre_de": "Schweden", "Capital": "Stockholm", "Población": 10549347},
    ]
    return dataset


def write_csv_readable(rows: List[Dict[str, Any]], dest: Path) -> None:
    if not rows:
        dest.write_text("")
        return
    headers = ["Nombre", "Nombre_es", "Nombre_de", "Capital", "Población"]
    with dest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json_readable(rows: List[Dict[str, Any]], dest: Path) -> None:
    with dest.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def write_csv_compact(rows: List[Dict[str, Any]], dest: Path) -> None:
    headers = ["Nombre", "Nombre_es", "Nombre_de", "Capital", "Población"]
    with dest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow([row.get(h, "") for h in headers])

def write_json_compact(rows: List[Dict[str, Any]], dest: Path) -> None:
    with dest.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))

def dict_to_xml_element(tag: str, mapping: Dict[str, Any]) -> ET.Element:
    elem = ET.Element(tag)
    for key, value in mapping.items():
        child = ET.Element(str(key))
        child.text = "" if value is None else str(value)
        elem.append(child)
    return elem


def build_xml_tree(rows: List[Dict[str, Any]]) -> ET.Element:
    root = ET.Element("paises")
    for row in rows:
        root.append(dict_to_xml_element("pais", row))
    return root


def pretty_print_xml(element: ET.Element) -> str:
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


def write_xml_readable(rows: List[Dict[str, Any]], dest: Path) -> None:
    root = build_xml_tree(rows)
    xml_string = pretty_print_xml(root)
    with dest.open("w", encoding="utf-8") as f:
        f.write(xml_string)

def write_xml_compact(rows: List[Dict[str, Any]], dest: Path) -> None:
    root = build_xml_tree(rows)
    xml_string = ET.tostring(root, encoding="unicode")
    with dest.open("w", encoding="utf-8") as f:
        f.write(xml_string)


def main() -> None:
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_dataset()

    # CSV
    write_csv_readable(rows, SCRIPT_DIR / "paises.csv")
    write_csv_compact(rows, SCRIPT_DIR / "paises.min.csv")

    # JSON
    write_json_readable(rows, SCRIPT_DIR / "paises.json")
    write_json_compact(rows, SCRIPT_DIR / "paises.min.json")

    # XML
    write_xml_readable(rows, SCRIPT_DIR / "paises.xml")
    write_xml_compact(rows, SCRIPT_DIR / "paises.min.xml")

    print(
        "Escritura completada:\n"
        f" - {SCRIPT_DIR / 'paises.csv'}\n"
        f" - {SCRIPT_DIR / 'paises.min.csv'}\n"
        f" - {SCRIPT_DIR / 'paises.json'}\n"
        f" - {SCRIPT_DIR / 'paises.min.json'}\n"
        f" - {SCRIPT_DIR / 'paises.xml'}\n"
        f" - {SCRIPT_DIR / 'paises.min.xml'}\n"
    )


if __name__ == "__main__":
    main()


