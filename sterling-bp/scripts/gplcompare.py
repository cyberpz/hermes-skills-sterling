"""Confronta due .gpl per struttura: visita il grafo dalla Start seguendo gli archi in ordine e confronta
nodo per nodo dati dell'attivita', archi (nome e stato) e posizione logica (layout / tipo di vista).
Gli ACTIVITYID e le coordinate non contano. Uso: python -I gplcompare.py <gpl_a> <gpl_b>"""
import sys
import xml.etree.ElementTree as ET


def canon(e):
    return (e.tag, (e.text or '').strip(), tuple(sorted(e.attrib.items())), tuple(canon(c) for c in e))


def load(path):
    r = ET.parse(path).getroot()
    nodes = {n.findtext('ACTIVITYID'): n for n in r.findall('GPLNODE')}
    where = {}
    for L in r.findall('GPLLAYOUT'):
        kind = 'root' if L.get('ID') == '0' else ('onfault' if L.get('GROUPID') else 'subflow:' + L.get('name'))
        for v in L.findall('GPLNODEVIEW'):
            where.setdefault(v.get('ID'), []).append((kind, v.get('TYPE')))
    start = [i for i, n in nodes.items() if n.findtext('NODECLASS') in ('1', '3')]
    assert len(start) == 1, start
    order, idx, stack = [], {}, [start[0]]
    while stack:
        i = stack.pop()
        if i in idx:
            continue
        idx[i] = len(order)
        order.append(i)
        stack += [e.findtext('GPLEDGEID') for e in reversed(nodes[i].findall('GPLEDGE'))]
    out = []
    for i in order:
        n = nodes[i]
        sig = (n.findtext('ACTIVITY'), n.findtext('INSTANCENAME'), n.findtext('NODECLASS'),
               n.findtext('SERVICEOPERATION') or '', '', canon(n.find('ACTIVITYDATA')))
        sm = n.findtext('SERVICEMESSAGE') or ''
        msg = n.find('ACTIVITYDATA/output')
        if sm and (msg is None or [x.text for x in msg if x.tag == 'value'][0] != sm):
            print('SERVICEMESSAGE diverso dal messaggio di output:', i, sm)
        edges = []
        for e in n.findall('GPLEDGE'):
            st = e.find('GPLEDGESTATE')
            edges.append((idx.get(e.findtext('GPLEDGEID'), 'MISSING:' + e.findtext('GPLEDGEID')),
                          e.findtext('GPLEDGENAME') or '', tuple(canon(c) for c in st) if st is not None else ()))
        out.append((sig, edges, tuple(where.get(i, []))))
    dangling = [e.findtext('GPLEDGEID') for n in nodes.values() for e in n.findall('GPLEDGE')
                if e.findtext('GPLEDGEID') not in nodes]
    noview = [i for i in nodes if len(where.get(i, [])) != 1]
    unreached = [i for i in nodes if i not in idx]
    return out, dict(nodi=len(nodes), archi_senza_nodo=dangling, nodi_senza_una_vista=noview, nodi_non_raggiunti=unreached)


def short(x, n=160):
    s = repr(x)
    return s if len(s) <= n else s[:n] + '...'


if __name__ == '__main__':
    a, ia = load(sys.argv[1])
    b, ib = load(sys.argv[2])
    print('A', ia)
    print('B', ib)
    diffs = 0
    for k in range(max(len(a), len(b))):
        if k >= len(a) or k >= len(b) or a[k] != b[k]:
            diffs += 1
            if diffs <= 15:
                print(f'--- nodo {k}')
                for lab, x in (('A', a[k] if k < len(a) else None), ('B', b[k] if k < len(b) else None)):
                    if x is None:
                        print(lab, None)
                        continue
                    print(lab, short(x[0][:3]), x[1], x[2])
                if k < len(a) and k < len(b) and a[k][0] != b[k][0]:
                    print('   dati diversi:', short(a[k][0][5], 400), '\n   vs', short(b[k][0][5], 400))
    print('nodi diversi:', diffs)
