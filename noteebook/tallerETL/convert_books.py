#!/usr/bin/env python3
"""
Extrae libros desde bookCatalog.xml y genera CSV/JSON/XML
en versiones legibles y compactas.

Entrada esperada:
  - data/bookCatalog.xml (relativa a este script)

Salidas:
  - books.csv, books.min.csv
  - books.json, books.min.json
  - books.xml, books.min.xml

Campos extraídos (en español para CSV/JSON):
  - Id, Título, Autor, Género, Precio, Fecha de publicación

Notas:
  - Para XML de salida se usan etiquetas seguras: id, title, author, genre, price, publish_date
  - El parser intenta detectar variantes comunes de nombres: title/título, author/autor, etc.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_XML = SCRIPT_DIR / "data" / "bookCatalog.xml"

DEST_CSV = SCRIPT_DIR / "books.csv"
DEST_CSV_MIN = SCRIPT_DIR / "books.min.csv"
DEST_JSON = SCRIPT_DIR / "books.json"
DEST_JSON_MIN = SCRIPT_DIR / "books.min.json"
DEST_XML = SCRIPT_DIR / "books.xml"
DEST_XML_MIN = SCRIPT_DIR / "books.min.xml"


SPANISH_HEADERS: List[str] = [
    "Id",
    "Título",
    "Autor",
    "Género",
    "Precio",
    "Fecha de publicación",
]

SAFE_XML_TAGS = {
    "Id": "id",
    "Título": "title",
    "Autor": "author",
    "Género": "genre",
    "Precio": "price",
    "Fecha de publicación": "publish_date",
}


def _text_of(element: Optional[ET.Element]) -> str:
    return "" if element is None else (element.text or "").strip()


def _find_first(element: ET.Element, names: List[str]) -> Optional[ET.Element]:
    # Busca el primer hijo cuyo tag coincida con alguna variante (case-insensitive)
    lower_names = {n.lower() for n in names}
    for child in list(element):
        if child.tag.lower() in lower_names:
            return child
    # XPath alternativa por si hay niveles intermedios
    for name in names:
        found = element.find(f".//{name}")
        if found is not None:
            return found
    return None


def parse_books(xml_path: Path) -> List[Dict[str, Any]]:
    if not xml_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo XML: {xml_path}")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Encontrar nodos de libro
    # Soporta estructuras como <catalog><book ...> o <bookstore><book ...>
    books_nodes = root.findall(".//book") if root.tag.lower() != "book" else [root]
    records: List[Dict[str, Any]] = []

    for b in books_nodes:
        # Id puede venir como atributo o como hijo <id>
        book_id = b.get("id") or _text_of(_find_first(b, ["id", "Id"]))
        title = _text_of(_find_first(b, ["title", "titulo", "título"]))
        author = _text_of(_find_first(b, ["author", "autor"]))
        genre = _text_of(_find_first(b, ["genre", "genero", "género"]))
        price = _text_of(_find_first(b, ["price", "precio"]))
        pub_date = _text_of(
            _find_first(
                b,
                [
                    "publish_date",
                    "publishdate",
                    "fecha_publicacion",
                    "fecha_de_publicacion",
                ],
            )
        )

        records.append(
            {
                "Id": book_id,
                "Título": title,
                "Autor": author,
                "Género": genre,
                "Precio": price,
                "Fecha de publicación": pub_date,
            }
        )

    return records


def write_csv_readable(rows: List[Dict[str, Any]], dest: Path) -> None:
    with dest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SPANISH_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in SPANISH_HEADERS})


def write_csv_compact(rows: List[Dict[str, Any]], dest: Path) -> None:
    with dest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow([row.get(h, "") for h in SPANISH_HEADERS])


def write_json_readable(rows: List[Dict[str, Any]], dest: Path) -> None:
    with dest.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def write_json_compact(rows: List[Dict[str, Any]], dest: Path) -> None:
    with dest.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))


def build_xml_tree(rows: List[Dict[str, Any]]) -> ET.Element:
    root = ET.Element("books")
    for row in rows:
        book_el = ET.Element("book")
        for human_key, safe_tag in SAFE_XML_TAGS.items():
            child = ET.Element(safe_tag)
            value = row.get(human_key, "")
            child.text = "" if value is None else str(value)
            book_el.append(child)
        root.append(book_el)
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


def xml_compact(element: ET.Element) -> str:
    return ET.tostring(element, encoding="unicode")


def main() -> None:
    rows = parse_books(DATA_XML)

    # CSV
    write_csv_readable(rows, DEST_CSV)
    write_csv_compact(rows, DEST_CSV_MIN)

    # JSON
    write_json_readable(rows, DEST_JSON)
    write_json_compact(rows, DEST_JSON_MIN)

    # XML
    root = build_xml_tree(rows)
    with DEST_XML.open("w", encoding="utf-8") as f:
        f.write(pretty_print_xml(root))
    with DEST_XML_MIN.open("w", encoding="utf-8") as f:
        f.write(xml_compact(root))

    print(
        "Escritura completada:\n"
        f" - {DEST_CSV}\n"
        f" - {DEST_CSV_MIN}\n"
        f" - {DEST_JSON}\n"
        f" - {DEST_JSON_MIN}\n"
        f" - {DEST_XML}\n"
        f" - {DEST_XML_MIN}\n"
    )


if __name__ == "__main__":
    main()







