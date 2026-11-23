"""Confronta il dizionario EDIFACT dell'input di una mappa con quello di altre mappe (es. D09A contro D01B).

Uso: python -I confronta_dizionario_edi.py <mappa.mxl> <riferimento1.mxl> [<riferimento2.mxl> ...]
Per ogni segmento usato (elenco `used` sotto, da adattare) confronta composite ed elementi nell'ordine, lunghezza e
tipo; stampa IDENTICO o le posizioni diverse. Riferimenti: mappe gia' in PROD con la versione del partner (stesso
directory = stessi segmenti). Le etichette D09A/D01B nell'output indicano solo "mappa" e "riferimento".
Regola: regole.md di questa skill, "Input".
"""
import sys, re
import xml.etree.ElementTree as ET
def load(path):
    root = ET.parse(path).getroot()
    for el in root.iter(): el.tag = el.tag.split('}')[-1]
    inp = root.find('INPUT'); segs = {}
    for s in inp.iter('Segment'):
        tag = s.findtext('BlockSig/Tag') or s.findtext('Name')
        if tag in segs: continue
        els = []
        for ch in s:
            if ch.tag == 'Composite':
                cn = ch.findtext('Name')
                for f in ch:
                    if f.tag == 'Field':
                        els.append((cn, re.sub(r':\d+$','',f.findtext('Name')), f.findtext('StoreLimit/MaxLen'), f.findtext('StoreLimit/DataType'), f.findtext('Mandatory')))
            elif ch.tag == 'Field':
                els.append(('-', re.sub(r':\d+$','',ch.findtext('Name')), ch.findtext('StoreLimit/MaxLen'), ch.findtext('StoreLimit/DataType'), ch.findtext('Mandatory')))
        segs[tag] = els
    return segs
fm = load(sys.argv[1]); ref = {}
for p in sys.argv[2:]:
    for k, v in load(p).items(): ref.setdefault(k, v)
used = ['BGM','DTM','TSR','MOA','FTX','CNT','TOD','LOC','RFF','TDT','NAD','CTA','COM','GID','HAN','TMP','RNG','MEA','DIM','PCI','GIN','DGS','SGP','EQD','EQN']
for tag in used:
    a = fm.get(tag); b = ref.get(tag)
    if b is None: print(f'{tag}: nessun riferimento D01B'); continue
    if a is None: print(f'{tag}: non presente nella mappa'); continue
    if [x[:2] for x in a] == [x[:2] for x in b] and [x[2:4] for x in a] == [x[2:4] for x in b]:
        print(f'{tag}: IDENTICO ({len(a)} elementi)'); continue
    print(f'{tag}: DIVERSO  D09A={len(a)} D01B={len(b)}')
    n = max(len(a), len(b))
    for i in range(n):
        x = a[i] if i < len(a) else None; y = b[i] if i < len(b) else None
        if x != y: print(f'   pos {i+1}: D09A={x}  D01B={y}')

