"""Compila un sorgente di mappa (.mxl o .map) nel Map Editor locale e stampa gli errori di compilazione.

Uso: python compila_mxl.py <mappa.mxl|.map>      (serve pywinauto; NON con -I se pywinauto e' nel site utente)

`Mapper.exe -c` dice solo "Impossibile compilare la mappa" senza il motivo: questo script apre la mappa,
lancia File > Compila, salva il .txo accanto al sorgente e legge l'elenco della finestra degli errori di
compilazione (righe ERRORE/AVVERTENZA con il numero di riga della regola). Chiude il Map Editor alla fine.
Le righe "Compilazione del loop ..." non vengono stampate.
Funziona con il Map Editor in italiano e in inglese: la voce di menu si cerca per testo (Compila / Compile) e le
finestre per classe (#32770, con un campo Edit quella del .txo, con un ListBox quella degli errori), non per titolo
("Nome oggetto di conversione" / "Translation Object Name", "Errori di compilazione" / "Compile Errors").
Map Editor in un percorso diverso dal default: modificare la costante MAPPER qui sotto.
"""
import os
import subprocess
import sys
import time

from pywinauto import Application

MAPPER = r'C:\Program Files (x86)\Sterling Commerce\Map Editor\Mapper.exe'
COMPILE = ('compila', 'compile')
SAVE = ('salva', 'save')


def label(ctrl):
    return ctrl.window_text().replace('&', '').split('\t')[0].strip().lower()


def dialogs(app):
    return [w for w in app.windows() if w.class_name() == '#32770' and w.is_visible()]


def wait_dialog(app, child_class, timeout):
    """Prima finestra di dialogo visibile che contiene un controllo della classe indicata."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for d in dialogs(app):
            if any(c.class_name() == child_class for c in d.descendants()):
                return d
        time.sleep(1)
    return None


def main(src):
    src = os.path.abspath(src)
    txo = os.path.splitext(src)[0] + '.txo'
    if os.path.exists(txo):
        os.remove(txo)   # cosi' 'TXO non creato' vuol dire davvero che la compilazione non l'ha scritto
    os.environ['__COMPAT_LAYER'] = 'RunAsInvoker'
    p = subprocess.Popen([MAPPER, src])
    try:
        time.sleep(30)
        app = Application(backend='win32').connect(process=p.pid)
        file_menu = app.top_window().menu().items()[0].sub_menu()
        voce = [i for i in file_menu.items() if i.text().replace('&', '').strip().lower().startswith(COMPILE)]
        if not voce:
            print('Voce Compila/Compile non trovata nel menu File:', [i.text() for i in file_menu.items()])
            return
        voce[0].select()

        save = wait_dialog(app, 'Edit', 60)
        if save is None:
            print('Finestra di salvataggio del .txo non comparsa; finestre:', [w.window_text() for w in app.windows()])
            return
        [c for c in save.descendants() if c.class_name() == 'Edit'][0].set_edit_text(txo)
        [c for c in save.descendants() if c.class_name() == 'Button' and label(c) in SAVE][0].click()
        # "Conferma Salva con nome / Confirm Save As": il .txo esiste gia' (es. nella cartella scelta dal Map
        # Editor) -> rispondere Si'/Yes, altrimenti la compilazione resta ferma e il .txo non viene aggiornato
        for _ in range(5):
            time.sleep(1)
            si = [c for d in dialogs(app) for c in d.descendants()
                  if c.class_name() == 'Button' and label(c) in ('sì', 'si', 'yes')]
            if si:
                si[0].click()
                break

        err = wait_dialog(app, 'ListBox', 180)
        if err is None:
            print('Finestra degli errori di compilazione non comparsa')
        else:
            for c in err.descendants():
                if c.class_name() == 'ListBox':
                    for t in c.item_texts():
                        if 'loop' not in t.lower():
                            print(t)
        time.sleep(2)
        print('TXO', txo if os.path.exists(txo) else 'non creato')
    finally:
        p.kill()


if __name__ == '__main__':
    main(sys.argv[1])
