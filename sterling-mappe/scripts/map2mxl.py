"""Converte mappe Sterling tra il formato binario .map e il formato XML .mxl, nei due sensi.

Usa il Map Editor installato (File > Salva con nome... > tipo .mxl o .map): la conversione la fa
IBM, lo script si limita a pilotarlo. Ogni mappa viene aperta in un processo Map Editor separato,
lanciato senza elevazione (__COMPAT_LAYER=RunAsInvoker) e chiuso alla fine: le finestre del
Map Editor gia' aperte dall'utente non vengono toccate.

Il senso dipende dall'estensione del file di partenza:
    .map (binario "GENTRAN TEMPLATE SOURCE") -> .mxl   per leggere o modificare la mappa
    .mxl (XML)                                -> .map   per caricarla su Sterling (+ .txo con mapper.exe -c)

Uso:
    python -I map2mxl.py MAPPA.map [ALTRA.map ...] [-o CARTELLA] [--force] [--no-validate]
    python -I map2mxl.py "<cartella>\\*.map" -o <cartella_mxl>
    python -I map2mxl.py MAPPA.mxl                    (scrive MAPPA.map)

Il file convertito esce accanto all'originale (o in -o) con lo stesso nome. Se esiste gia' non
viene sovrascritto senza --force. Codice di uscita: 0 tutto ok, 1 almeno una mappa non convertita,
2 requisiti mancanti (Map Editor o pywinauto).

Il dialogo "Salva con nome" si riconosce dal campo nome file, non dal titolo: il titolo cambia
con la lingua del Map Editor/Windows ("Salva con nome", "Save As", "Guardar como"...).

Requisiti: Windows, Map Editor installato (percorso diverso dal default: variabile
d'ambiente MAP_EDITOR_DIR), `python -m pip install --user pywinauto`.
Con `python -I` il site-packages dell'utente e' escluso: lo script lo riaggiunge da solo,
cosi' resta la protezione di -I (niente moduli presi dalla cartella corrente).
"""
import argparse
import glob
import os
import shutil
import site
import subprocess
import sys
import tempfile
import time
import warnings
import xml.etree.ElementTree as ET

os.environ["__COMPAT_LAYER"] = "RunAsInvoker"  # niente UAC: stesso livello di Python
warnings.simplefilter("ignore")  # pywinauto avvisa di Python 64 bit su app 32 bit

if sys.flags.isolated:  # python -I: pywinauto di solito sta nel site-packages dell'utente
    site.addsitedir(site.getusersitepackages())
try:
    from pywinauto import Application
    from pywinauto.timings import TimeoutError as PwaTimeout
    import win32con
    import win32gui
except ImportError as e:
    print(f"map2mxl: manca pywinauto ({e}). Installarlo una volta con:  python -m pip install --user pywinauto",
          file=sys.stderr)
    sys.exit(2)

warnings.filterwarnings("ignore", message="32-bit application")

MAP_EDITOR_DIR = os.environ.get("MAP_EDITOR_DIR") or r"C:\Program Files (x86)\Sterling Commerce\Map Editor"
MAPPER_EXE = os.path.join(MAP_EDITOR_DIR, "Mapper.exe")
MAPPER_XSD = os.path.join(MAP_EDITOR_DIR, "Schemas", "Mapper.xsd")
MXL_NS = "http://www.stercomm.com/SI/Map"

ID_FILE_SAVE_AS = 57604      # comando MFC standard "Salva con nome..."
ID_FNAME_EDIT = 1148         # dialogo Salva: campo nome file
ID_FTYPE_COMBO = 1136        # dialogo Salva: tipo file
ID_OK = 1

BINARY_HEADER = b"GENTRAN TEMPLATE SOURCE"


class ConvError(Exception):
    pass


class ConvTimeout(ConvError):
    """Il Map Editor non ha finito in tempo: si riprova una volta con un processo nuovo."""


def open_windows(app):
    """Finestre visibili del processo, per capire dove si e' fermato il Map Editor."""
    out = []
    for w in app.windows():
        try:
            if w.is_visible():
                out.append(dialog_text(w) if w.class_name() == "#32770" else f"{w.class_name()} '{w.window_text()}'")
        except Exception:
            pass
    return "; ".join(out) or "nessuna"


def dialog_text(dlg):
    """Testo leggibile di un dialogo inatteso (messaggi d'errore del Map Editor)."""
    parts = [dlg.window_text()]
    for c in dlg.descendants():
        t = c.window_text().strip()
        if t and c.class_name() in ("Static", "Button"):
            parts.append(t)
    return " | ".join(p for p in parts if p)


def is_large_map_warning(dlg):
    """L'unico dialogo a cui lo script risponde da solo: mappa grande, propone .MAP.

    Testo IT: 'Questa mappa contiene un numero molto elevato di oggetti ... Premere OK per
    salvare la mappa utilizzando il formato di file ".MXL"'. Si riconosce dalle due
    estensioni citate, cosi' funziona anche con il Map Editor in un'altra lingua.
    """
    text = dialog_text(dlg)
    return '".MAP"' in text and '".MXL"' in text


def is_progress(dlg):
    """Finestra di avanzamento (mappe grandi): ha una barra di progresso."""
    try:
        return any(c.class_name() == "msctls_progress32" for c in dlg.descendants())
    except Exception:  # la finestra si e' chiusa mentre la leggevamo
        return True


def other_dialogs(app, exclude=()):
    out = []
    for w in app.windows(class_name="#32770"):
        if w.handle not in exclude and w.is_visible():
            out.append(w)
    return out


def is_save_dialog(dlg):
    """Il dialogo Salva ha il campo nome file e il combo del tipo: vale in ogni lingua."""
    try:
        ids = {(c.control_id(), c.class_name()) for c in dlg.descendants()}
    except Exception:  # la finestra si e' chiusa mentre la leggevamo
        return False
    return (ID_FNAME_EDIT, "Edit") in ids and (ID_FTYPE_COMBO, "ComboBox") in ids


def wait_save_dialog(app, timeout):
    """Aspetta il dialogo "Salva con nome" (qualunque sia il titolo) e lo restituisce."""
    end = time.time() + timeout
    while time.time() < end:
        for d in other_dialogs(app):
            if is_save_dialog(d):
                return app.window(handle=d.handle)  # specifica, come prima: ha child_window()
        time.sleep(0.3)
    dlgs = other_dialogs(app)
    raise ConvError("salva con nome: " + (dialog_text(dlgs[0]) if dlgs else "il dialogo non e' comparso"))


def wait_file_stable(path, timeout):
    """Aspetta che il file esista e smetta di crescere."""
    end = time.time() + timeout
    last = -1
    while time.time() < end:
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size > 0 and size == last:
                return True
            last = size
        time.sleep(0.7)
    return False


def convert_one(src_path, dst_path, timeout=90):
    """Apre src_path nel Map Editor e lo salva come dst_path (.map -> .mxl oppure .mxl -> .map)."""
    to_map = dst_path.lower().endswith(".map")
    src_ext, dst_ext = (".mxl", ".map") if to_map else (".map", ".mxl")
    work = tempfile.mkdtemp(prefix="map2mxl_")
    # nome semplice: niente spazi/parentesi nel percorso passato al Map Editor
    src = os.path.join(work, "m" + src_ext)
    dst = os.path.join(work, "m" + dst_ext)
    shutil.copyfile(src_path, src)
    app = None
    try:
        app = Application(backend="win32").start(f'"{MAPPER_EXE}" "{src}"', wait_for_idle=False)
        main = app.window(class_name_re=r"Afx:00400000:.*", top_level_only=True)
        main.wait("exists visible", timeout=timeout)

        # la mappa e' aperta quando compare la finestra MDI con il percorso nel titolo
        end = time.time() + timeout
        while True:
            titles = [c.window_text() for c in main.children()]
            if any(t.lower().endswith("m" + src_ext) for t in titles):
                break
            dlgs = other_dialogs(app)
            if dlgs:
                raise ConvError("apertura: " + dialog_text(dlgs[0]))
            if time.time() > end:
                raise ConvError("apertura: la mappa non si e' aperta entro il timeout")
            time.sleep(0.5)

        win32gui.PostMessage(main.handle, win32con.WM_COMMAND, ID_FILE_SAVE_AS, 0)
        dlg = wait_save_dialog(app, timeout=30)

        # tipo file = quello di destinazione (.mxl: se il Map Editor lo propone)
        combo = dlg.child_window(control_id=ID_FTYPE_COMBO, class_name="ComboBox")
        types = combo.item_texts()
        other_ext = src_ext
        type_idx = next((i for i, t in enumerate(types)
                         if f"*{dst_ext})" in t.lower() and f"*{other_ext}" not in t.lower()), None)
        if type_idx is None:
            hint = " (manca MSXML 6?)" if not to_map else ""
            raise ConvError(f"salva con nome: tipo {dst_ext} non disponibile{hint} tipi=" + repr(types))
        combo.select(type_idx)
        time.sleep(0.5)  # il cambio di tipo puo' riscrivere il nome file: si scrive dopo
        save_dlg = dlg.handle  # prima del click: dopo il dialogo non esiste piu'

        def press_save():
            edit = dlg.child_window(control_id=ID_FNAME_EDIT, class_name="Edit")
            edit.set_edit_text(dst)
            if edit.window_text() != dst:
                raise ConvError(f"salva con nome: il nome file non si scrive (c'e' {edit.window_text()!r})")
            dlg.child_window(control_id=ID_OK, class_name="Button").click()

        press_save()
        answered = set()
        retried_click = False
        t_click = time.time()
        end = t_click + timeout
        while not wait_file_stable(dst, 2):
            # dialogo Salva ancora aperto dopo qualche secondo: il click non e' arrivato (primo avvio lento)
            if (win32gui.IsWindow(save_dlg) and win32gui.IsWindowVisible(save_dlg)
                    and time.time() - t_click > 5 and not other_dialogs(app, exclude=(save_dlg,))):
                if retried_click:
                    raise ConvTimeout("salva con nome: il dialogo resta aperto dopo due click su Salva; finestre aperte: "
                                      + open_windows(app))
                press_save()
                retried_click = True
                t_click = time.time()
                continue
            for d in other_dialogs(app, exclude=(save_dlg,) + tuple(answered)):
                if is_progress(d):
                    continue  # "Salvataggio di ... / Avanzamento totale": basta aspettare
                if is_large_map_warning(d):
                    # avviso "mappa con molti oggetti, meglio .MAP": OK = salva comunque in .MXL
                    ok = [c for c in d.children() if c.class_name() == "Button" and c.control_id() == ID_OK]
                    if not ok:
                        raise ConvError("salvataggio: avviso mappa grande senza pulsante OK")
                    ok[0].click()
                    answered.add(d.handle)
                    continue
                raise ConvError("salvataggio: " + dialog_text(d))
            if time.time() > end:
                raise ConvTimeout(f"salvataggio: il {dst_ext} non e' stato scritto entro il timeout; finestre aperte: "
                                  + open_windows(app))
        # il Map Editor potrebbe ancora scrivere: aspetta qualche secondo di stabilita'
        wait_file_stable(dst, 5)
        if to_map:
            check_map(dst)
        else:
            check_mxl(dst)
        shutil.copyfile(dst, dst_path)
    finally:
        if app is not None:
            try:
                app.kill()
            except Exception:
                pass
        shutil.rmtree(work, ignore_errors=True)


def check_map(path):
    with open(path, "rb") as fh:
        head = fh.read(len(BINARY_HEADER))
    if head != BINARY_HEADER:
        raise ConvError("il file salvato non e' un .map binario")


def check_mxl(path):
    with open(path, "rb") as fh:
        head = fh.read(200)
    if not head.lstrip().startswith(b"<?xml"):
        raise ConvError("il file salvato non e' XML")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        raise ConvError(f"XML non ben formato: {e}")
    if root.tag != f"{{{MXL_NS}}}Mapper":
        raise ConvError(f"radice inattesa {root.tag}")


def validate_xsd(paths):
    """Valida i .mxl con Mapper.xsd usando .NET (niente librerie Python in piu')."""
    if not paths or not os.path.exists(MAPPER_XSD):
        return {}
    lst = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    lst.write("\n".join(paths)); lst.close()
    ps = r"""
$set = New-Object System.Xml.Schema.XmlSchemaSet
$null = $set.Add('%s', '%s')
foreach ($f in (Get-Content -LiteralPath '%s' -Encoding UTF8)) {
  $n = 0; $first = ''
  $st = New-Object System.Xml.XmlReaderSettings; $st.ValidationType = 'Schema'; $st.Schemas = $set
  $st.add_ValidationEventHandler({ param($o,$e) $script:n++; if (-not $script:first) { $script:first = "r$($e.Exception.LineNumber): $($e.Message)" } })
  $script:n = 0; $script:first = ''
  $r = [System.Xml.XmlReader]::Create($f, $st); while ($r.Read()) {}; $r.Close()
  "$f`t$script:n`t$script:first"
}
""" % (MXL_NS, MAPPER_XSD.replace("'", "''"), lst.name.replace("'", "''"))
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                              "[Console]::OutputEncoding=[Text.Encoding]::UTF8;" + ps],
                             capture_output=True, text=True, encoding="utf-8")
    finally:
        os.unlink(lst.name)
    out = {}
    for line in res.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            out[parts[0]] = (int(parts[1]), parts[2])
    return out


def main():
    ap = argparse.ArgumentParser(description="Converte mappe Sterling .map -> .mxl e .mxl -> .map tramite il Map Editor.")
    ap.add_argument("maps", nargs="+", help="file .map/.mxl o pattern (es. <cartella>\\*.map)")
    ap.add_argument("-o", "--out", help="cartella di destinazione (default: accanto al file di partenza)")
    ap.add_argument("--force", action="store_true", help="sovrascrive i file di destinazione esistenti")
    ap.add_argument("--no-validate", action="store_true", help="salta la validazione con Mapper.xsd")
    ap.add_argument("--timeout", type=int, default=90, help="secondi massimi per ogni passo (default 90)")
    args = ap.parse_args()

    if not os.path.exists(MAPPER_EXE):
        print(f"map2mxl: Map Editor non trovato: {MAPPER_EXE} (installato altrove? impostare MAP_EDITOR_DIR)",
              file=sys.stderr)
        sys.exit(2)

    files = []
    for p in args.maps:
        files.extend(sorted(glob.glob(p)) if any(ch in p for ch in "*?") else [p])
    if args.out:
        os.makedirs(args.out, exist_ok=True)

    done, failed, skipped = [], [], []
    for f in files:
        f = os.path.abspath(f)
        name, ext = os.path.splitext(os.path.basename(f))
        to_map = ext.lower() == ".mxl"
        out = os.path.join(args.out or os.path.dirname(f), name + (".map" if to_map else ".mxl"))
        if not os.path.isfile(f):
            failed.append((f, "file non trovato")); continue
        with open(f, "rb") as fh:
            head = fh.read(200)
        if to_map:
            if not head.lstrip(b"\xef\xbb\xbf \r\n\t").startswith(b"<?xml"):
                skipped.append((f, "estensione .mxl ma non e' XML")); continue
        elif not head.startswith(BINARY_HEADER):
            skipped.append((f, "non e' un .map binario")); continue
        if os.path.exists(out) and not args.force:
            skipped.append((f, f"esiste gia' {out} (usa --force)")); continue
        t0 = time.time()
        try:
            try:
                convert_one(f, out, timeout=args.timeout)
            except ConvTimeout as e:
                print(f"RIPROVO {os.path.basename(f)}: {e}", flush=True)
                convert_one(f, out, timeout=args.timeout)
            done.append(out)
            print(f"OK    {os.path.basename(f)} -> {out}  ({time.time() - t0:.0f}s)", flush=True)
        except Exception as e:  # noqa: BLE001 - riportiamo tutto e passiamo alla prossima
            failed.append((f, str(e)))
            print(f"ERR   {os.path.basename(f)}: {e}", flush=True)

    done_mxl = [p for p in done if p.lower().endswith(".mxl")]
    if done_mxl and not args.no_validate:
        for path, (n, first) in validate_xsd(done_mxl).items():
            if n:
                print(f"XSD   {os.path.basename(path)}: {n} problemi, il primo {first}")
            else:
                print(f"XSD   {os.path.basename(path)}: valido")

    for f, why in skipped:
        print(f"SKIP  {os.path.basename(f)}: {why}")
    print(f"\nConvertite {len(done)}, saltate {len(skipped)}, errori {len(failed)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
