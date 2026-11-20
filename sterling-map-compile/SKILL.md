---
name: sterling-map-compile
description: "Use to compile Sterling maps headless under Wine, no GUI."
version: 1.0.0
author: Giuseppe Vitale
license: MIT
metadata:
  hermes:
    tags: [sterling-b2b, edi, wine, map-editor]
    related_skills: [sterling-edi-ops]
---

# Sterling Map compile headless (Mapper.exe sotto Wine) — VERIFICATO

## When to Use
Compilare o validare mappe Sterling B2B (`.mxl` XML, `.map` GENTRAN binario → `.txo`/`.ltx`) senza aprire il Map Editor GUI: validazione di surgery su mxl (es. bug righe >300 char), ciclo dump-DB→edit→compile.

## Asset necessari (macchina Linux)
- Cartella Map Editor COMPLETA (exe + DLL + Mapper.xsd + Standards Library, es. 8.0.3.0) copiata da un'installazione Windows
- Cartella tool: `setup_wine_mapeditor.sh` (setup riproducibile), `mapper_wine.sh` (runner), `compile_map.py` (variante Windows nativa)
- Wine prefix win32: `~/.wine-mapper`

## Uso (giornaliero)
```bash
bash <WORKDIR>/mapper_wine.sh /path/mappa.mxl [altra.mxl ...]
# [OK] nome.mxl -> nome.txo (N byte) / [KO] + testo dialog OCR — VERDETTO finale, exit code
```
Runner gestisce: copia in cartella editor, Xvfb, dialog modali (OCR + Return via xdotool), verifica magic `WOODSTOCK TEMPLATE`.

## Setup (solo macchina nuova — riprodotto da setup_wine_mapeditor.sh)
1. `wine64` + `wine32:i386` + xvfb xdotool x11-utils imagemagick tesseract-ocr(-ita) cabextract wmctrl; winetricks da GitHub (non è in apt main).
2. Prefisso **win32**: `WINEARCH=win32 WINEPREFIX=~/.wine-mapper wine wineboot`.
3. `winetricks --force msxml4 vcrun6 comctl32 gdiplus` (winetricks via xvfb-run), poi `xvfb-run wine regsvr32 /s msxml4.dll`.
4. **`wine reg add HKCU\Software\Wine\DllOverrides /v msxml4 /d builtin /f`** — il native MS 2009 NON va, il builtin di Wine sì.
5. **CHIAVE (senza questo ogni mxl dà "This file uses an unsupported syntax" — errore ingannevole)**: dalla cartella editor `wine reg import mapper.reg` + `xvfb-run wine regsvr32 /s` delle DLL `Converter EncFile XmlValidationComponent Encodings EncDetector`. Il zip della cartella editor porta i FILE ma non le registrazioni COM dell'installer.

## Sintassi Mapper.exe -c (doc IBM "Compiling Maps Using the Command Line")
- `Mapper.exe -c nome.mxl` con **cwd = cartella che contiene la mappa** e argomento **basename** (o relativo alla cartella editor): path assoluto con cwd altrove → `ShellExecuteEx failed: File not found` o dialog usage.
- `.txo` scritto nella stessa cartella del sorgente; wildcard `*.mxl` ok, niente ricorsione.
- `-s <numericType>` salva cambiando tipo mappa (24 = Sterling B2B). `/S` con slash NON è il flag di compile: apre dialog usage bloccante. Flag corretto `-c` (o `/c`).
- In `-c` mode la finestra principale resta unmapped; su errore/confirm apre **dialog modale ~332x82** che blocca il processo: chiuderlo con `xdotool windowactivate --sync <win> key Return`; identificarlo tra le finestre `xdotool search --name "Map Editor"` con altezza <200px (`xwininfo`).

## Verifica compilazione
- Exit 0 **e** `.txo` generato **e** magic bytes iniziali `WOODSTOCK TEMPLATE` (stesso magic dei .txo di produzione).
- `grep -c <stringa>` sul `.txo`: le stringhe degli script restano visibili — conferma presenza/assenza di testo atteso dopo una patch.
- La validazione **semantica** definitiva resta check-in + run di test su Sterling: dichiararlo sempre.

## Ciclo di allineamento mappa vs spec partner (workflow standard)
1. Cartella di lavoro dedicata per ticket: copia `*_FIXED.map`, spec salvata a terra, dump testuale (`mappa_dump.txt` + script con offset) per audit. L'originale non si tocca mai.
2. Diff campo-per-campo contro la spec → tabella per campo: richiesto / presente oggi (con evidenza: stringa e offset reali della mappa, mai contenuti inventati) / verdetto OK–DA-FARE–N/A / fattibilità (same-length vs GUI/mxl). Campi N/A motivati, non silenziosi.
3. Applicare SOLO patch same-length; compilare anche la baseline originale (a parte) per confronto, poi rimuoverne l'output.
4. Report con prima/dopo per campo; consegna con hash.
5. Verifica post-compile (rifarla di persona se il lavoro è di un delegato — l'auto-report non è un fatto): exit 0, magic `WOODSTOCK TEMPLATE`, `grep -c` della stringa introdotta (1× nel txo patchato, 0× nell'originale), `cmp -l` originale→patchata con byte count = solo la patch, sha256 di input/output.
6. Campi che richiedono insert strutturale → fase mxl: la conversione `.map`→`.mxl` esiste SOLO nel Map Editor GUI (Salva come XML) su Windows — `mapper.exe -c` compila e basta, nessuna flag headless di conversione. Far convertire la mappa GIÀ patchata (l'mxl nasce con la patch dentro) e riaprire la .mxl esportata nell'editor prima di consegnarla: è il gate di validazione dell'export.
7. Fase 2 sulla .mxl ricevuta: prima di tutto `grep` del marcatore della patch binaria (es. il valore introdotto) — se manca, è stata convertita l'originale: riapplicare la patch via surgery mxl (costa meno di una riconversione). Insert in mxl: duplicare il `<Segment>` fratello nell'OUTPUT con ID unico sopra il max del file, `<Link>` solo se il campo input esiste; compilare con `mapper_wine.sh` (accetta .mxl) e set-diff dump nuova vs originale.
8. Consegna fase 2: `FIXED.mxl` + `FIXED.txo` + report aggiornato con prima/dopo per campo e hash; re-import e test run su Sterling restano all'operatore con accesso all'ambiente.
9. Dichiarare sempre che la validazione semantica definitiva resta re-import + test run su Sterling.

## Pitfall
- Per leggere dialog/screenshot senza vision API: `import -window <win>` + `tesseract` (OCR).
- `.map` è GENTRAN binary template: ogni statement length-prefixed (1 byte). Patch same-length (padding spazi attorno a `=`) sicura; il Map Editor la ricompila. Contenuto testuale estraibile con `strings`/Python (script inline in chiaro, CRLF).
- **Segmenti ereditati da una mappa clonata sono spesso Active=0** (mai emessi in output): attivarli per una patch NON è una modifica neutra — cambia l'output di produzione su tutto il flusso (es. nuovo NAD o FTX su tutte le fatture). Segnalarlo esplicitamente nel report come modifica impattante e pretendere test mirato prima del check-in.
- **Insert strutturali (nuovi segmenti) nel .map binario vietati** — la tabella offset del formato GENTRAN non tollera insert. Classificare ogni modifica richiesta come *same-length patch* (si applica) o *insert strutturale* (non forzare: riportare nel report come «richiede Map Editor GUI / conversione mxl» con segmento esatto e punto di innesto nello script). `mapper_wine.sh` accetta anche il `.map` (stesso flusso del `.mxl`, `.txo` accanto al sorgente).
- CHM d'aiuto incorporato: `7z x MapEditor.chm` → HTML (tabella numeric map types: `r_STDS_ME_NumericMapTypes.html`).
- `regsvr32` senza `/s` apre message box e si appende: sempre `/s`.
- MSXML4 va registrato (`regsvr32 /s msxml4.dll`) anche se winetricks l'ha già copiato.
- Regex di sicurezza per query SQL verso il DB Sterling (whitelist SELECT, `dbms_` bloccato tranne `dbms_lob.getlength`) nel tool di dump.

## Collegamenti
- Struttura mxl, surgery a testo, dump mappe, dove sta la mappa nel DB (MAP/MAP_VERSIONS/DATA_TABLE blob zippato): skill `sterling-edi-ops`, riferimento `references/sterling-mxl-maps.md`.
