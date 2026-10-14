"""Compile the project's simple PO catalogs without an external msgfmt binary."""

import ast
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def compile_catalog(po_path: Path) -> None:
    entries = {}
    current = {}

    def store_entry():
        if "msgid" not in current:
            return
        key = current["msgid"]
        if "msgid_plural" in current:
            key += "\0" + current["msgid_plural"]
            value = current["msgstr[0]"] + "\0" + current["msgstr[1]"]
        else:
            value = current.get("msgstr", "")
        entries[key.encode("utf-8")] = value.encode("utf-8")
        current.clear()

    for raw_line in (*po_path.read_text(encoding="utf-8").splitlines(), ""):
        line = raw_line.strip()
        if not line:
            store_entry()
            continue
        if line.startswith("#"):
            continue
        name, _, quoted = line.partition(" ")
        if name not in {"msgid", "msgid_plural", "msgstr", "msgstr[0]", "msgstr[1]"}:
            raise ValueError(f"Unsupported PO syntax: {po_path}: {line}")
        current[name] = ast.literal_eval(quoted)

    keys = sorted(entries)
    count = len(keys)
    original_table = []
    translated_table = []
    payload = bytearray()
    offset = 28 + count * 16
    for key in keys:
        original_table.append((len(key), offset + len(payload)))
        payload.extend(key + b"\0")
    for key in keys:
        value = entries[key]
        translated_table.append((len(value), offset + len(payload)))
        payload.extend(value + b"\0")

    output = bytearray(struct.pack("<7I", 0x950412DE, 0, count, 28, 28 + count * 8, 0, 0))
    for length, position in original_table + translated_table:
        output.extend(struct.pack("<2I", length, position))
    output.extend(payload)
    po_path.with_suffix(".mo").write_bytes(output)


if __name__ == "__main__":
    for catalog in (ROOT / "locale").glob("*/LC_MESSAGES/django.po"):
        compile_catalog(catalog)
