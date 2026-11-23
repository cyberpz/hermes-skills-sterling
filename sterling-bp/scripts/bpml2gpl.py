"""Genera lo stercomm.gpl (diagramma GPM di Sterling B2B Integrator) a partire da uno stercomm.bpml.

Uso: python -I bpml2gpl.py <bpml> <gpl_out> [--subflow "NOME1|NOME2"] [--template a.gpl,b.gpl]
     (di solito non si chiama da solo: lo usa crea_bp.py)

- Tipo di servizio di ogni participant (ACTIVITY del nodo): da activity_map.json (servizi e adapter standard IBM);
  un participant nuovo (es. un JavaTask o un adapter configurato da voi) si aggiunge ad activity_map.json oppure
  passando con --template il .gpl di un BP che lo usa.
- Formato (vedi ../formato-bp-gpm.md): un GPLNODE per attivita', GPLEDGEID = nodo successivo; sequence Start ->
  figli -> End; onFault in un GPLLAYOUT a parte (GROUPID); choice con un arco per case; subflow = sequence disegnata
  come riquadro con un layout proprio.
- Impaginazione (vedi ../regole.md, "Struttura e diagramma GPM"): flusso da sinistra a destra; choice con piu' rami a
  meta' tra il primo e l'ultimo ramo, choice end alla stessa altezza; choice con un ramo solo sulla linea e il ramo un
  livello sotto; fine dei rami allineate; layout dell'onFault col nome della sequence che contiene, senza prefisso SS.
- Provato rigenerando i gpl di BP esportati dal GPM: stessa struttura (nodi, archi, dati); un gpl generato e' stato
  aperto e risalvato dal GPM senza differenze di struttura (solo coordinate).
"""
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET

STEP, ROW = 110, 90


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') \
        .replace("'", '&apos;').replace('"', '&quot;')


def fv(field, value):
    return f'<field>{field}</field>\n<value>{esc(value)}</value>\n'


def load_templates(paths=()):
    """participant -> (ACTIVITY, '', ''): prima activity_map.json, poi gli eventuali .gpl passati"""
    t = {}
    amap = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'activity_map.json')
    for part, act in json.load(open(amap, encoding='utf-8')).items():
        t[part] = (act, '', '')
    for p in paths:
        for n in ET.parse(p).getroot().findall('GPLNODE'):
            ad = n.find('ACTIVITYDATA')
            if ad.get('name') != 'Operation_Activity':
                continue
            kv = dict(zip([x.text for x in ad if x.tag == 'field'], [x.text for x in ad if x.tag == 'value']))
            t[kv['participantName']] = (n.findtext('ACTIVITY') or '', '', '')
    return t


class Gen:
    def __init__(self, templates, subflows):
        self.t, self.subflows = templates, subflows
        self.nodes = {}          # id -> dict
        self.order = []
        self.layouts = [{'name': '', 'id': 0, 'group': '', 'views': [], 'lviews': [], 'gviews': []}]
        self.next_id = 1762590000000
        self.next_group = 1

    # --- nodi e layout -------------------------------------------------------------------------
    def node(self, layout, x, y, adname, adbody, activity, instname, nodeclass, vtype='', w=80, so='', sm=''):
        nid = str(self.next_id)
        self.next_id += 10
        self.nodes[nid] = dict(id=nid, adname=adname, adbody=adbody, activity=activity, inst=instname,
                               cls=nodeclass, edges=[], so=so, sm=sm)
        self.order.append(nid)
        self.layouts[layout]['views'].append((nid, x, y, 48, w, vtype))
        return nid

    def edge(self, src, dst, name='', state=''):
        self.nodes[src]['edges'].append((dst, name, state))

    def new_layout(self, name, group=''):
        lid = len(self.layouts)
        self.layouts.append({'name': name, 'id': lid, 'group': group, 'views': [], 'lviews': [], 'gviews': []})
        return lid

    # --- attivita' -----------------------------------------------------------------------------
    def assigns(self, elem):
        out = ''
        for a in elem.findall('assign'):
            out += '<Oper_Assign_Activity>\n'
            if a.get('from') is not None:
                out += fv('from', a.get('from')) + fv('to', a.get('to'))
            else:
                out += fv('to', a.get('to')) + fv('constant', a.text or '')
            out += fv('append', 'true' if a.get('append') == 'true' else 'false') + '</Oper_Assign_Activity>\n'
        return out

    @staticmethod
    def star_pos(elem):
        a = elem.findall('assign') if elem is not None else []
        st = [i for i, x in enumerate(a) if x.get('to') == '.' and x.get('from') == '*']
        return None if not st else st[0]

    def operation(self, e, layout, x, y):
        part = e.find('participant').get('name')
        if part not in self.t:
            raise SystemExit(f'participant sconosciuto: {part}. Esportare un BP che lo usa (Export-SterlingSource.ps1) e '
                             f'passarne il .gpl con --template, oppure aggiungerlo ad activity_map.json')
        activity = self.t[part][0]
        out, inp = e.find('output'), e.find('input')
        # nei gpl esportati SERVICEOPERATION e' sempre ProcessData; SERVICEMESSAGE e' vuoto oppure il messaggio di output
        so, sm = 'ProcessData', (out.get('message') if out is not None else '')
        ip = self.star_pos(inp)
        op = self.star_pos(out)
        imode = '2' if ip is not None else '1'
        omode = '3' if op == 0 else ('4' if op is not None else '1')
        body = fv('name', e.get('name')) + fv('participantName', part) + fv('inputMessageMode', imode) \
            + fv('outputMessageMode', omode)
        for tag, el in (('output', out), ('input', inp)):
            if el is not None:
                body += f'<{tag}>\n' + fv('message', el.get('message')) + self.assigns(el) + f'</{tag}>\n'
        nid = self.node(layout, x, y, 'Operation_Activity', body, activity, e.get('name'), '5', so=so, sm=sm)
        return nid, [nid]

    def assign(self, e, layout, x, y):
        body = fv('name', e.get('name'))
        if e.get('from') is not None:
            body += fv('from', e.get('from')) + fv('to', e.get('to'))
        else:
            body += fv('to', e.get('to')) + fv('constant', e.text or '')
        body += fv('append', 'true' if e.get('append') == 'true' else 'false')
        nid = self.node(layout, x, y, 'Assign_Activity', body, 'Assign_Activity', e.get('name'), '6')
        return nid, [nid]

    def repeat(self, e, layout, x, y):
        body = fv('name', e.get('name')) + fv('ref', e.get('ref'))
        nid = self.node(layout, x, y, 'Repeat_Activity', body, 'Repeat_Activity', e.get('name'), '6')
        return nid, [nid]

    # --- impaginazione -------------------------------------------------------------------------
    # Ogni blocco ha una linea (la y dei suoi nodi principali) e occupa w in larghezza, up sopra e down sotto.
    # Regole di impaginazione: choice con piu' rami all'altezza centrale dei rami, e cosi' la sua end;
    # choice con un ramo solo: start ed end sulla linea, il ramo un livello sotto; fine dei rami allineate.
    def measure(self, e):
        t = e.tag
        if t in ('operation', 'assign', 'repeat'):
            return STEP, 0, 0
        if t == 'sequence':
            if e.get('name') in self.subflows:
                return STEP, 0, 0
            kids = [self.measure(c) for c in e if c.tag != 'onFault']
            w = STEP + sum(k[0] for k in kids) + STEP
            up = max([0] + [k[1] for k in kids])
            down = max([0] + [k[2] for k in kids])
            if e.find('onFault') is not None:
                down = max(down, ROW)
            return w, up, down
        if t == 'choice':
            br = [self.measure(x) for x in self.branches(e)]
            if len(br) == 1:
                bw, bu, bd = br[0]
                return max(bw, 2 * STEP), 0, ROW + bu + bd
            _, up, down = self.branch_lines(br)
            return STEP + max(w for w, _, _ in br) + STEP, up, down
        raise SystemExit('elemento non gestito: ' + t)

    @staticmethod
    def branch_lines(ms):
        """linee dei rami impilati, relative alla linea della choice, che sta a meta' tra il primo e l'ultimo ramo"""
        lines, cur = [], 0
        for _, u, d in ms:
            lines.append(cur + u)
            cur += u + d + ROW
        mid = (lines[0] + lines[-1]) // 2
        return [ln - mid for ln in lines], mid, (cur - ROW) - mid

    def branches(self, e):
        acts = {c.get('name'): c for c in e if c.tag != 'select'}
        return [acts[c.get('activity')] for c in e.find('select').findall('case')]

    def chain_measure(self, children):
        m = [self.measure(c) for c in children]
        return max([0] + [k[1] for k in m]), max([0] + [k[2] for k in m])

    def chain(self, children, layout, x, y, first_src):
        """collega first_src -> figli in fila sulla linea y; ritorna (uscite, x finale)"""
        exits, cx = [first_src], x
        for c in children:
            entry, ex = self.build(c, layout, cx, y)
            for s in exits:
                self.edge(s, entry)
            exits, cx = ex, cx + self.measure(c)[0]
        return exits, cx

    def sequence(self, e, layout, x, y, end_x=None):
        name = e.get('name')
        children = [c for c in e if c.tag != 'onFault']
        fault = e.find('onFault')
        if name in self.subflows:
            child = self.new_layout(name)
            self.layouts[layout]['lviews'].append((child, x, y, 48, 80))
            ly = 40 + self.chain_measure(children)[0]
            start = self.node(child, 40, ly, 'Sequence_Start_Activity', fv('name', name), '', 'Start', '6', 'SFSTART', 40)
            exits, cx = self.chain(children, child, 40 + STEP, ly, start)
            end = self.node(child, cx, ly, 'Sequence_End_Activity', '', '', 'End', '6', 'SFEND', 40)
            own_layout, gx, gy = child, 40, ly + ROW
        else:
            start = self.node(layout, x, y, 'Sequence_Start_Activity', fv('name', name), 'Sequence_Start_Activity',
                              name, '6')
            exits, cx = self.chain(children, layout, x + STEP, y, start)
            end = self.node(layout, max(cx, end_x or 0), y, 'Sequence_End_Activity', '', 'Sequence_End_Activity',
                            'Sequence End', '6')
            own_layout, gx, gy = layout, x, y + ROW
        for s in exits:
            self.edge(s, end)
        if fault is not None:
            g = self.next_group
            self.next_group += 1
            self.layouts[own_layout]['gviews'].append((g, gx, gy, 48, 81))
            # nome del layout = nome della sequence contenuta, senza il prefisso SS (come nei gpl esportati:
            # 'SS ERROR FOR EACH' -> 'ERROR FOR EACH', 'SS_onError' -> 'onError')
            inner = [c.get('name') for c in fault if c.tag == 'sequence']
            label = inner[0] if len(inner) == 1 else f'onFault {name}'
            for pre in ('SS_', 'SS '):
                if label.startswith(pre):
                    label = label[len(pre):]
            fl = self.new_layout(label, str(g))
            fy = 40 + self.chain_measure(list(fault))[0]
            # il codice dell'onFault (<onFault code="OnError">) va nel nodo di partenza, altrimenti il GPM al
            # salvataggio rigenera un <onFault> senza codice, che intercetta tutti gli errori
            ofdata = fv('name', 'OnFault Start') + (fv('code', fault.get('code')) if fault.get('code') else '')
            ofs = self.node(fl, 40, fy, 'OnFault_Start_Activity', ofdata, '', 'OnFault Start',
                            '6', 'OFSTART', 73)
            fex, fcx = self.chain(list(fault), fl, 40 + STEP, fy, ofs)
            ofe = self.node(fl, fcx, fy, 'OnFault_End_Activity', '', '', 'OnFault End', '6', 'OFEND', 69)
            for s in fex:
                self.edge(s, ofe)
            self.edge(start, ofs)
        return start, [end]

    def choice(self, e, layout, x, y):
        name = e.get('name')
        start = self.node(layout, x, y, 'Choice_Start_Activity', fv('name', name), 'Choice_Start_Activity', name, '6')
        cases = e.find('select').findall('case')
        acts = self.branches(e)
        ms = [self.measure(a) for a in acts]
        exits = []
        if len(acts) == 1:
            bw, bu, _ = ms[0]
            places = [(x, y + ROW + bu)]
            end_col = x + max(bw - STEP, STEP)
            seq_end = end_col
        else:
            maxw = max(w for w, _, _ in ms)
            places = [(x + STEP, y + dl) for dl in self.branch_lines(ms)[0]]
            end_col = x + STEP + maxw
            seq_end = end_col - STEP
        for case, act, (bx, by) in zip(cases, acts, places):
            if act.tag == 'sequence' and act.get('name') not in self.subflows:
                entry, ex = self.sequence(act, layout, bx, by, end_x=seq_end)
            else:
                entry, ex = self.build(act, layout, bx, by)
            neg = 'true' if case.get('negative') == 'true' else 'false'
            state = f"<case activity='{esc(case.get('activity'))}' ref='{esc(case.get('ref'))}' negative='{neg}' />\n"
            self.edge(start, entry, case.get('ref') + '..', state)
            exits += ex
        end = self.node(layout, end_col, y, 'Choice_End_Activity', '', 'Choice_End_Activity', 'Choice End', '6')
        for s in exits:
            self.edge(s, end)
        return start, [end]

    def build(self, e, layout, x, y):
        return {'operation': self.operation, 'assign': self.assign, 'repeat': self.repeat,
                'sequence': self.sequence, 'choice': self.choice}[e.tag](e, layout, x, y)

    # --- processo ------------------------------------------------------------------------------
    def process(self, root):
        rules = ''.join('<Rule_Config>\n' + fv('name', r.get('name')) + fv('condition', r.findtext('condition'))
                        + '</Rule_Config>\n' for r in root.findall('rule'))
        top = [c for c in root if c.tag != 'rule']
        y0 = 40 + self.chain_measure(top)[0]
        start = self.node(0, 40, y0, 'Process_Activity', fv('name', root.get('name').strip()) + rules, '', 'start',
                          '3', 'MFSTART', 40)
        exits, cx = self.chain(top, 0, 40 + STEP, y0, start)
        end = self.node(0, cx, y0, '', '', '', 'End', '4', 'MFEND', 40)
        for s in exits:
            self.edge(s, end)

    def render(self):
        o = ['<GPL language="BPML" langversion="v0_3" gplversion="1.1.1">\n']
        for nid in self.order:
            n = self.nodes[nid]
            o.append('<GPLNODE>\n')
            o.append(f"\t<SERVICEOPERATION>{esc(n['so'])}</SERVICEOPERATION>\n\t<SERVICEMESSAGE>{esc(n['sm'])}</SERVICEMESSAGE>\n")
            o.append(f"\t<ACTIVITYDATA name=\"{n['adname']}\">\n{n['adbody']}\n\t</ACTIVITYDATA>\n")
            o.append(f"\t<ANNOTATION></ANNOTATION>\n\t<ACTIVITYNAME></ACTIVITYNAME>\n\t<ACTIVITYID>{nid}</ACTIVITYID>\n")
            o.append(f"\t<ACTIVITY>{esc(n['activity'])}</ACTIVITY>\n\t<INSTANCENAME>{esc(n['inst'])}</INSTANCENAME>\n")
            o.append(f"\t<NODECLASS>{n['cls']}</NODECLASS>\n")
            for dst, name, state in n['edges']:
                o.append(f"\t<GPLEDGE><GPLEDGEID>{dst}</GPLEDGEID>\n\t<GPLEDGENAME>{esc(name)}</GPLEDGENAME>\n"
                         f"<GPLEDGESTATE>{state}</GPLEDGESTATE>\n</GPLEDGE>\n")
            o.append('</GPLNODE>\n')
        for L in self.layouts:
            o.append(f"<GPLLAYOUT name=\"{esc(L['name'])}\" ID=\"{L['id']}\" SYNCID=\"\" GROUPID=\"{L['group']}\">\n")
            o.append('\t<ANNOTATION></ANNOTATION>\n')
            for nid, x, y, h, w, t in L['views']:
                o.append(f'<GPLNODEVIEW ID="{nid}" XCOORD="{x}" YCOORD="{y}" HEIGHT="{h}" WIDTH="{w}" TYPE="{t}" />\n')
            for lid, x, y, h, w in L['lviews']:
                o.append(f'<GPLLAYOUTVIEW ID="{lid}" XCOORD="{x}" YCOORD="{y}" HEIGHT="{h}" WIDTH="{w}" TYPE="SUBFLOW" />\n')
            for gid, x, y, h, w in L['gviews']:
                o.append(f'<GPLGROUPLAYOUTVIEW ID="{gid}" XCOORD="{x}" YCOORD="{y}" HEIGHT="{h}" WIDTH="{w}" TYPE="ONFAULT" />\n')
            o.append('</GPLLAYOUT>\n')
        o.append('</GPL>\n')
        return ''.join(o)


def generate(bpml_path, subflows=(), templates=()):
    g = Gen(load_templates(templates), set(subflows))
    g.process(ET.parse(bpml_path).getroot())
    return g


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('bpml')
    ap.add_argument('gpl_out')
    ap.add_argument('--subflow', default='', help='nomi delle sequence da disegnare come subflow, separati da |')
    ap.add_argument('--template', default='', help='.gpl da cui prendere il tipo di participant non in activity_map.json')
    a = ap.parse_args()
    g = generate(a.bpml, [x for x in a.subflow.split('|') if x], [x for x in a.template.split(',') if x])
    open(a.gpl_out, 'w', encoding='utf-8', newline='\n').write(g.render())
    print(f'{a.gpl_out}: {len(g.nodes)} nodi, {len(g.layouts)} layout')
