"""Elenca i campi di una mappa .mxl con tipo/formato e, per l'output, il campo di input collegato.

Uso: python -I campi_link_mxl.py <mappa.mxl>
"""
import sys, xml.etree.ElementTree as ET

M = '{http://www.stercomm.com/SI/Map}'
root = ET.parse(sys.argv[1]).getroot()
campi = {}
for lato in ('INPUT', 'OUTPUT'):
    for f in root.find(f'.//{M}{lato}').iter(f'{M}Field'):
        sl = f.find(f'{M}StoreLimit')
        campi[f.findtext(f'{M}ID')] = dict(
            lato=lato, nome=f.findtext(f'{M}Name'), tipo=sl.findtext(f'{M}DataType') if sl is not None else '',
            formato=sl.findtext(f'{M}Format') if sl is not None else '', maxlen=sl.findtext(f'{M}MaxLen') if sl is not None else '',
            link=f.findtext(f'{M}Link'))
# Con input XML il link punta all'ID del record _pcd_ che contiene il campo, non al campo:
# per risolverlo si guarda il primo Field del record con quell'ID.
record_campo = {}
for el in root.find(f'.//{M}INPUT').iter():
    rid = el.findtext(f'{M}ID')
    if rid and rid not in campi:
        f = el.find(f'.//{M}Field')
        if f is not None:
            record_campo[rid] = f.findtext(f'{M}ID')
for i, c in campi.items():
    if c['lato'] == 'OUTPUT':
        link = c['link'] or ''
        src = campi.get(link) or campi.get(record_campo.get(link, ''), {})
        nome = src.get('nome') or (f'?? link {link} non trovato' if link else '- (nessun link)')
        print(f"OUT {c['nome']:<28} id={i:<4} {c['tipo']:<9} fmt={c['formato']!r:<22} <- {nome} ({src.get('tipo', '')} fmt={src.get('formato', '')!r})")
