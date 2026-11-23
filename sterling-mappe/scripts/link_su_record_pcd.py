"""Sposta i link dell'output dal Field di input al suo record _pcd_, come li scrive il Map Editor per un
input XML (verificato confrontando mappe salvate dal Map Editor: i link sono tutti verso _pcd_).
Tocca solo i <Link> dei campi di output che puntano a un Field figlio di un XMLRecord.
Uso: python -I link_su_record_pcd.py <mappa.mxl> <mappa in uscita.mxl>
"""
import re, sys, xml.etree.ElementTree as ET

src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding='utf-8').read()
M = '{http://www.stercomm.com/SI/Map}'
inp = ET.fromstring(t).find(f'.//{M}INPUT')
padre = {c: p for p in inp.iter() for c in p}
verso_record = {f.findtext(f'{M}ID'): padre[f].findtext(f'{M}ID') for f in inp.iter(f'{M}Field')
                if padre[f].tag == f'{M}XMLRecord'}
o = t.index('<OUTPUT>')
spostati = [0]


def relink(m):
    v = m.group(1)
    if v in verso_record:
        spostati[0] += 1
        return f'<Link>{verso_record[v]}</Link>'
    return m.group(0)


out = t[:o] + re.sub(r'<Link>(\d+)</Link>', relink, t[o:])
ET.fromstring(out)
with open(dst, 'w', encoding='utf-8', newline='\n') as fo:
    fo.write(out)
print(f'link spostati sul record _pcd_: {spostati[0]} su {len(re.findall("<Link>", t[o:]))}')
