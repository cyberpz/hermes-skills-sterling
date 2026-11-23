"""Stampa la struttura di una mappa Sterling .mxl: albero di input e output, regole estese e link.

Uso: python -I dump_mxl.py <mappa.mxl>
"""
import sys, xml.etree.ElementTree as ET

M = '{http://www.stercomm.com/SI/Map}'
GRUPPI = ('Group', 'PosRecord', 'VarDelimRecord', 'XMLElementGroup', 'XMLParticleGroup', 'XMLRecord', 'Record')


def nome(e):
    return (e.findtext(f'{M}XMLTag') or e.findtext(f'{M}Name') or '').strip()


def regola(e):
    r = e.find(f'{M}ExplicitRule')
    if r is None:
        return ''
    parti = []
    for k in ('OnBegin', 'OnEnd', 'Rule'):
        v = (r.findtext(f'{M}{k}') or '').strip()
        if v:
            parti.append(f'{k}: {v}')
    return ' || '.join(parti)


def albero(e, liv, lato):
    for c in e:
        t = c.tag.replace(M, '')
        if t in GRUPPI:
            print(f'{"  " * liv}[{t}] {nome(c)} id={c.findtext(f"{M}ID")} min={c.findtext(f"{M}Min")} max={c.findtext(f"{M}Max")}')
            rg = regola(c)
            if rg:
                print(f'{"  " * liv}   REGOLA {rg[:3000]}')
            albero(c, liv + 1, lato)
        elif t == 'Field':
            extra = []
            for k in ('StartPos', 'Length', 'MaxLength', 'Mandatory', 'DataType', 'Format'):
                v = c.findtext(f'{M}{k}')
                if v not in (None, ''):
                    extra.append(f'{k}={v}')
            lnk = c.find(f'.//{M}Link')
            sr = c.find(f'{M}StandardRule')
            srt = ''
            if sr is not None:
                srt = ' STD=' + ' '.join(f'{x.tag.replace(M, "")}:{(x.text or "").strip()}' for x in sr.iter() if (x.text or '').strip())[:300]
            print(f'{"  " * liv}- {nome(c)} id={c.findtext(f"{M}ID")} {" ".join(extra)}{srt}')
            rg = regola(c)
            if rg:
                print(f'{"  " * liv}   REGOLA {rg[:3000]}')
        elif t not in ('ExplicitRule',):
            albero(c, liv, lato)


root = ET.parse(sys.argv[1]).getroot()
for lato in ('INPUT', 'OUTPUT'):
    print(f'================ {lato}')
    albero(root.find(f'.//{M}{lato}'), 0, lato)
print('================ LINK')
for l in root.iter(f'{M}Link'):
    print(' '.join(f'{x.tag.replace(M, "")}={(x.text or "").strip()}' for x in l if (x.text or '').strip()))
