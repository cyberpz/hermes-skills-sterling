"""Stampa le coordinate dei nodi di un .gpl per layout e segnala nodi sovrapposti.
Uso: python -I gpllayout.py <gpl> [--quiet]"""
import sys
import xml.etree.ElementTree as ET

r = ET.parse(sys.argv[1]).getroot()
quiet = '--quiet' in sys.argv
nodes = {n.findtext('ACTIVITYID'): n for n in r.findall('GPLNODE')}
over = 0
for L in r.findall('GPLLAYOUT'):
    views = L.findall('GPLNODEVIEW')
    boxes = [(v.get('ID'), int(v.get('XCOORD')), int(v.get('YCOORD'))) for v in views]
    boxes += [('subflow ' + v.get('ID'), int(v.get('XCOORD')), int(v.get('YCOORD'))) for v in L.findall('GPLLAYOUTVIEW')]
    boxes += [('onfault ' + v.get('ID'), int(v.get('XCOORD')), int(v.get('YCOORD'))) for v in L.findall('GPLGROUPLAYOUTVIEW')]
    if not quiet:
        print('LAYOUT', L.get('ID'), repr(L.get('name')), 'gruppo', L.get('GROUPID'))
        for i, x, y in sorted(boxes, key=lambda b: (b[1], b[2])):
            n = nodes.get(i)
            lab = (n.findtext('ACTIVITYDATA/value') or n.findtext('INSTANCENAME')) if n is not None else i
            print(f'  x={x:>5} y={y:>4}  {lab}')
    for k, (i, x, y) in enumerate(boxes):
        for j, x2, y2 in boxes[k + 1:]:
            if abs(x - x2) < 90 and abs(y - y2) < 60:
                over += 1
                print(f'  SOVRAPPOSTI in layout {L.get("ID")}: {i} ({x},{y}) e {j} ({x2},{y2})')
    if any(y < 0 or x < 0 for _, x, y in boxes):
        print('  COORDINATE NEGATIVE nel layout', L.get('ID'))
print('sovrapposizioni:', over)
