"""Dal BPML al .bp da aprire nel GPM: controlla il BPML, genera il diagramma (.gpl) e impacchetta lo zip.

Uso: python -I crea_bp.py <bpml> [<out.bp>] [--like <bp di partenza.bp>] [--subflow "A|B"] [--force]

- <out.bp>   default: %USERPROFILE%\\Downloads\\<nome del file bpml>.bp
- --like     il .bp da cui si e' partiti (es. quello scaricato con Export-SterlingSource.ps1): ne riprende i subflow
             (sequence disegnate come riquadro) e i tipi di participant, cosi' il diagramma resta simile all'originale
- --subflow  subflow in piu' (nomi di sequence separati da |)

Controlli sul BPML (si ferma se c'e' un errore):
- XML valido; ogni case punta a una regola esistente e a un'attivita' figlia della sua choice; regole non usate (avviso);
- ogni repeat punta a un antenato con quel nome; nomi di sequence, choice e repeat univoci (regole.md);
- contenuto di ogni onFault = una sola sequence (come negli onFault esportati dal GPM);
- nessun onFault dentro il contenuto di un altro onFault (un solo livello: con onFault annidati il gestore non gira).
Controlli sul diagramma: ogni arco punta a un nodo esistente, ogni nodo ha una vista, nessun nodo sovrapposto.
"""
import argparse
import collections
import os
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True   # niente __pycache__ accanto agli script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpml2gpl  # noqa: E402


def check_bpml(path):
    errs, warns = [], []
    root = ET.parse(path).getroot()
    parent = {c: p for p in root.iter() for c in p}
    rules = {r.get('name') for r in root.findall('rule')}
    used = set()
    for ch in root.iter('choice'):
        kids = {c.get('name') for c in ch if c.tag != 'select'}
        for case in ch.find('select').findall('case'):
            used.add(case.get('ref'))
            if case.get('ref') not in rules:
                errs.append(f"choice '{ch.get('name')}': la regola '{case.get('ref')}' non esiste")
            if case.get('activity') not in kids:
                errs.append(f"choice '{ch.get('name')}': l'attivita' '{case.get('activity')}' non e' figlia della choice")
    for r in sorted(rules - used):
        warns.append(f"regola non usata: '{r}'")
    names = collections.Counter(e.get('name') for e in root.iter() if e.tag in ('sequence', 'choice', 'repeat'))
    for n, c in names.items():
        if c > 1:
            errs.append(f"nome usato {c} volte (sequence/choice/repeat devono essere univoci): '{n}'")
    for rp in root.iter('repeat'):
        p, ok = rp, False
        while p in parent:
            p = parent[p]
            if p.get('name') == rp.get('ref'):
                ok = True
                break
        if not ok:
            errs.append(f"repeat '{rp.get('name')}': '{rp.get('ref')}' non e' un antenato del repeat")
    for of in root.iter('onFault'):
        kids = list(of)
        if len(kids) != 1 or kids[0].tag != 'sequence':
            errs.append(f"onFault di '{parent[of].get('name')}': il contenuto deve essere una sola sequence "
                        f"(trovato {[k.tag for k in kids]})")
        for inner in of.iter('onFault'):
            if inner is not of:
                errs.append(f"onFault di '{parent[of].get('name')}' contiene l'onFault di '{parent[inner].get('name')}': "
                            f"un solo livello di onFault (con onFault annidati non gira nessuno step del gestore, "
                            f"vedi regole.md)")
    return errs, warns


def check_gpl(g):
    errs = []
    ids = set(g.nodes)
    for n in g.nodes.values():
        for dst, _, _ in n['edges']:
            if dst not in ids:
                errs.append(f"arco verso un nodo inesistente: {n['inst']} -> {dst}")
    seen = collections.Counter(v[0] for L in g.layouts for v in L['views'])
    errs += [f'nodo senza una sola vista: {i}' for i in ids if seen[i] != 1]
    for L in g.layouts:
        boxes = [(v[0], v[1], v[2]) for v in L['views']] + [(f'subflow {v[0]}', v[1], v[2]) for v in L['lviews']] \
            + [(f'onfault {v[0]}', v[1], v[2]) for v in L['gviews']]
        for k, (a, x, y) in enumerate(boxes):
            for b, x2, y2 in boxes[k + 1:]:
                if abs(x - x2) < 90 and abs(y - y2) < 60:
                    errs.append(f"nodi sovrapposti nel layout '{L['name']}': {a} e {b}")
    return errs


def like_info(bp):
    """subflow e file .gpl temporaneo dal .bp di partenza"""
    gpl = zipfile.ZipFile(bp).read('stercomm.gpl')
    r = ET.fromstring(gpl)
    sub = [L.get('name') for L in r.findall('GPLLAYOUT') if L.get('ID') != '0' and not L.get('GROUPID')]
    return sub, gpl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bpml')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--like')
    ap.add_argument('--subflow', default='')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    out = a.out or os.path.join(os.path.expanduser('~'), 'Downloads',
                                os.path.splitext(os.path.basename(a.bpml))[0] + '.bp')
    if os.path.exists(out) and not a.force:
        raise SystemExit(f'esiste gia\': {out} (usa --force per sovrascriverlo)')

    errs, warns = check_bpml(a.bpml)
    for w in warns:
        print('AVVISO', w)
    if errs:
        for e in errs:
            print('ERRORE', e)
        raise SystemExit('BPML non valido: nessun .bp creato')

    subflows = [x for x in a.subflow.split('|') if x]
    templates = []
    if a.like:
        sub, gpl = like_info(a.like)
        subflows += sub
        tmp = out + '.like.gpl'
        open(tmp, 'wb').write(gpl)
        templates.append(tmp)
    try:
        g = bpml2gpl.generate(a.bpml, subflows, templates)
    finally:
        for t in templates:
            os.remove(t)
    gerr = check_gpl(g)
    if gerr:
        for e in gerr:
            print('ERRORE', e)
        raise SystemExit('diagramma non valido: nessun .bp creato')

    bpml_bytes = open(a.bpml, 'rb').read().replace(b'\r\n', b'\n')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('stercomm.bpml', bpml_bytes)
        z.writestr('stercomm.gpl', g.render().encode('utf-8'))
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        ET.fromstring(z.read('stercomm.bpml'))
        ET.fromstring(z.read('stercomm.gpl'))
    missing = set(subflows) - {L['name'] for L in g.layouts}
    print(f'creato {out}: {len(g.nodes)} nodi, {len(g.layouts)} layout'
          + (f'; subflow non trovati nel BPML: {sorted(missing)}' if missing else ''))


if __name__ == '__main__':
    main()
