# Sterling MXL maps — analysis and text-mode editing

## Where the map lives in the Sterling DB (sources: Sterling community posts via Wayback — not official IBM doc)

- Source retrieval: some community sites are now parked domains — fetch pages via `web.archive.org/web/2023/<url>` and sift the HTML with stdlib.

- Metadata: table `MAP` = one row per map VERSION; `MAP_VERSIONS` = one row per map (holds `MAP_NAME`) — clean name list: `SELECT MAP_NAME FROM MAP_VERSIONS`.
- Content (.mxl/.map source and compiled .txo/.ltx): **zipped** BLOB in `DATA_TABLE` (generic versioned-document storage — same mechanism for BP and web templates), header in `DATA_HEADERS`. Oracle size: `dbms_lob.getlength(<blob col>)`.
- You cannot export from the blob via plain SQL: either unzip the blob (it is zipped) or use the product's export tool/UI. Download from the Maps UI = the normal way.
- Exact join column names (MAP→DATA_HEADERS/DATA_TABLE) may vary: discover them on the real DB with `select table_name, column_name, column_id from user_tab_columns where table_name in ('MAP','MAP_VERSIONS','DATA_HEADERS','DATA_TABLE') order by 1,2`.
- Bridge tool pattern: a SELECT-only dumper with a whitelist of named queries in a JSON file, bind-only, blob→magic-detect→unzip (stdlib zipfile). Flow: `discover` → fix joins → `run list_maps` → `dump <MAP> --version N`.

- **IBM-documented headless compilation**: `mapper.exe -c <file.mxl|pattern*.mxl>` (Map Editor Guide, "Compiling Maps Using the Command Line") — the .txo is written next to the source, no subfolder recursion, prerequisite MSXML 4.0 on the machine. Variant `-c -s 24` also saves forcing the Sterling B2B map type. Post-compile check: .txo newer than the source, else out-of-sync. Runs natively on Windows **or** headless on Linux via Wine (below).

### Map Editor headless on Linux via Wine

- Setup (Debian trixie): `sudo dpkg --add-architecture i386 && sudo apt install wine64 wine32:i386 xvfb` (wine 10), then 32-bit prefix: `WINEARCH=win32 WINEPREFIX=~/.wine-mapper wine wineboot` (the `err:setupapi ... Unsupported style` lines are harmless).
- `winetricks` is NOT installable via apt on `main`-only sources (it lives in contrib): download the single script from `raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks` → `~/.local/bin/winetricks`.
- MSXML 4.0 (prerequisite to read/write .mxl): `WINEPREFIX=~/.wine-mapper xvfb-run -a winetricks --force -q msxml4` — `--force` is mandatory because the Microsoft installer has expired signatures; verify `drive_c/windows/system32/msxml4.dll` (~1.3 MB).
- Execution: `WINEPREFIX=~/.wine-mapper xvfb-run -a wine mapper.exe -c <file.mxl>` (Xvfb needed because mapper.exe initializes the GUI even in -c mode).
- You need the COMPLETE Map Editor folder (exe + DLLs + Mapper.xsd + standard libraries), not just mapper.exe; MSXML inside the prefix, not the system.

Headless compile under Wine VERIFIED: `mapper.exe -c` works, but the editor must first be initialized in the Wine prefix — without these steps every .mxl fails with "This file uses an unsupported syntax. It cannot be opened." (misleading: it is a setup problem, not the map).

Key setup points, in order of importance:
1. **Import `mapper.reg`** (`wine reg import mapper.reg` from the editor folder) + **regsvr32 /s** of the DLLs `Converter EncFile XmlValidationComponent Encodings EncDetector` — WITHOUT this, mxl reading always fails. The editor folder zip carries the FILES but not the installer's COM registrations.
2. Dedicated **win32** prefix (`WINEARCH=win32`), wine 10 Debian + wine32:i386.
3. **msxml4 override = builtin** (`wine reg add HKCU\Software\Wine\DllOverrides /v msxml4 /d builtin /f`) — the native MS 2009 one does NOT work, Wine's builtin does. winetricks msxml4 only works with --force.
4. Launch `mapper.exe -c` **from the installation folder** with the file inside it (it resolves relatives from there); under Xvfb; on error/confirm it opens a **modal dialog ~332x82 to close with Return via xdotool** (the main window stays unmapped in -c mode).
5. Output verification: magic bytes `WOODSTOCK TEMPLATE` (same magic as production .txo files).

Note: definitive validation of a compiled .txo remains check-in + test run on Sterling; the magic match is strong evidence but not semantic proof.

## When to Use
When a `.mxl` file exported from the Map Editor arrives (new partner, clone of an existing map, xlate audit) and you need to understand or change its logic without opening Map Editor.

## Structure (verified on a PRICAT D96A map, SerializationVersion 33056)

- XML, namespace `http://www.stercomm.com/SI/Map`, CRLF. Root children: `MapDetails`, `TemplateOption`, `ExtendedRuleLibraries`, `INPUT`, `OUTPUT`, `SyntaxTokens`, `ConstantMap`, `Accumulators`.
- `MapDetails/Summary/Description` often reveals **which map the current one was cloned from**: read it first, it explains constants and rules inherited from the old partner.
- `INPUT/PosSyntax`: flat records of the extract (Group → PosRecord → Field). `OUTPUT/EDISyntax`: Group/Segment/Field tree of the EDI syntax.
- **The mapping links are the `<Link>` elements**: every output node contains `<Link>` with the source node's `<ID>`. There are NO `MapRef`/`Translation`/`SourceID`/`TargetID` — grepping those names returns 0 and wrongly suggests "the map has no mappings".
- Hardcoded logic (GLN, VAT, partner aliases, season conversions, product-specific fixes) lives in **`<ExplicitRule>`** elements (extended rule language, see rules in SKILL.md) and `ConstantMap` (100+ constants). This is what to sanitize when cloning a map for a new partner: hunt placeholder fake VATs and old-partner values.

## Recipe: full map dump

Ready script: `scripts/dump_map.py MAPPA.mxl out.json` → JSON with `desc` (clone of origin), `links` (resolved source→target), `rules` (non-empty ExplicitRule), `constants`. To compare two sibling maps (same ancestor cloned for different partners): dump both and set-diff links and rules. **From the sibling you copy DECISIONS (rule text, VAT/GLN/alias values), NEVER the links**: partner EDI structures differ and the same element IDs point at different nodes — a randomly copied link targets the wrong segment.

## Recipe: rebuild the mapping table (stdlib Python)

```python
import xml.etree.ElementTree as ET
NS={'m':'http://www.stercomm.com/SI/Map'}
r=ET.parse('MAPPA.mxl').getroot()
def txt(p,par):
    x=par.find('m:'+p,NS); return x.text if x is not None else None
idmap={}
for side in ('INPUT','OUTPUT'):
    def walk(n,path):
        for c in n:
            if c.tag.split('}')[1] in ('Group','PosRecord','Segment','Field','Element','Composite','SubElement'):
                nid=txt('ID',c); nm=txt('Name',c) or txt('Code',c) or ''
                p=path+'/'+(nm or c.tag.split('}')[1])
                if nid: idmap[nid]=p
                walk(c,p)
            else: walk(c,path)
    walk(r.find('m:'+side,NS),side)
# then: second walk over OUTPUT, for each node with a <Link> child print idmap[Link.text] -> path
```

## Recipe: edit the map without Map Editor

- **Never re-serialize with ElementTree** (it rewrites namespace prefixes and loses CRLF): do **surgery on the raw text** and write a NEW file (never touch the original export).
- Rule edit = `str.replace` of the exact `<ExplicitRule>` body text (rules are plain text inside the element); to remove one, replace it with empty text.
- Re-link an output field: with ET find the target field's `<ID>` and the new source's `<ID>`, then in the raw text find `<ID>{field_id}</ID>` and replace the first `<Link>{old}</Link>` occurring before the next `</Field>`.
- **`Name` of repeated fields carries a `:N` suffix** (e.g. `3039:6`, `IMD:13`): search the exact full name with suffix, otherwise you match the wrong field or none.
- Mandatory verification before delivering: re-parse XML (well-formed) + re-dump with `dump_map.py` + set-diff against the original dump → **exactly** the intended change must emerge, zero side effects. Deliver the new file with its hash.

## Pitfalls

- Before editing, keep the untouched original for the diff; text edits via targeted patch on unique XML fragments (nodes repeat numeric IDs: anchor Name+ID together).
- Well-formed XML ≠ valid map: real validation is re-import into Map Editor + test run — never declare the change working before that.
- **Audit inherited fixed-position `mid()`/`left()`/`right()` SKU slices in cloned rules**: if the brand's style prefix has variable length (e.g. 19 OR 20 chars), a cloned map slicing at fixed positions extracts wrong color/article on a double-digit % of styles.
- Rules contain product-specific fixes of the source partner (matches on specific article codes): flag them as removal candidates when the map serves a different partner.
