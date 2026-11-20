#!/usr/bin/env python3
"""Dump an xlsx sheet to TSV using stdlib only (no openpyxl needed to READ).

Usage: xlsx_dump_stdlib.py <file.xlsx> [sheet_name_or_index]
Default: first sheet. Resolves sharedStrings and inlineStr cells.
Row output: <row_number>\t<col0>\t<col1>...
"""
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

M = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def col_idx(ref):
    m = re.match(r"([A-Z]+)", ref)
    n = 0
    for ch in m.group(1):
        n = n * 26 + ord(ch) - 64
    return n - 1


def shared_strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(f"{{{M}}}t"))
            for si in root.iter(f"{{{M}}}si")]


def sheet_path(z, target):
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target")
            for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    sheets = wb.findall(f".//{{{M}}}sheets/{{{M}}}sheet")
    names = [s.get("name") for s in sheets]
    if target is None:
        i = 0
    elif target.isdigit() and int(target) < len(sheets):
        i = int(target)
    elif target in names:
        i = names.index(target)
    else:
        sys.exit(f"sheet {target!r} not found; available: {names}")
    tgt = rels[sheets[i].get(RID)]
    for cand in (tgt, tgt.lstrip("/"), "xl/" + tgt.lstrip("/")):
        if cand in z.namelist():
            return cand, names[i]
    sys.exit(f"cannot resolve path for sheet: {tgt}")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    target = sys.argv[2] if len(sys.argv) > 2 else None
    z = zipfile.ZipFile(path)
    shared = shared_strings(z)
    fn, sname = sheet_path(z, target)
    root = ET.fromstring(z.read(fn))
    print(f"# sheet: {sname}", file=sys.stderr)
    for row in root.iter(f"{{{M}}}row"):
        cells = {}
        for c in row.iter(f"{{{M}}}c"):
            t, val = c.get("t"), ""
            if t == "inlineStr":
                is_el = c.find(f"{{{M}}}is")
                if is_el is not None:
                    val = "".join(x.text or "" for x in is_el.iter(f"{{{M}}}t"))
            else:
                v = c.find(f"{{{M}}}v")
                val = v.text if v is not None else ""
                if t == "s" and val != "":
                    val = shared[int(val)]
            cells[col_idx(c.get("r"))] = val
        maxc = max(cells) if cells else -1
        out = [str(cells.get(i, "")).replace("\t", " ").replace("\n", " ")
               for i in range(maxc + 1)]
        print(f"{row.get('r')}\t" + "\t".join(out))


if __name__ == "__main__":
    main()
