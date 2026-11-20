#!/usr/bin/env python3
"""Dump di una mappa Sterling .mxl in JSON: descrizione (rivela il clone di origine),
link risolti sorgente->target, ExplicitRule non vuote, costanti.
Uso: python3 dump_map.py MAPPA.mxl out.json
Confronto tra due mappe sorelle: dumparle entrambe e fare set-diff su links/rules."""
import xml.etree.ElementTree as ET, json, sys
NS={'m':'http://www.stercomm.com/SI/Map'}
def tag(e): return e.tag.split('}')[1]
def txt(p,parent):
    x=parent.find('m:'+p,NS); return x.text if x is not None else None
def dump(path):
    t=ET.parse(path); r=t.getroot()
    out={'file':path}
    md=r.find('m:MapDetails/m:Summary',NS)
    out['desc']=txt('Description',md); out['author']=txt('Author',md)
    idmap={}
    NODES=('Group','PosRecord','Segment','Field','Element','Composite','SubElement','ElementOpt','SubElementOpt')
    def collect(side):
        root=r.find('m:'+side,NS)
        def walk(n,path_):
            for c in n:
                tg=tag(c)
                if tg in NODES:
                    nid=txt('ID',c); nm=txt('Name',c) or txt('Code',c) or ''
                    p=path_+'/'+(nm or tg)
                    if nid: idmap[nid]=(side,p)
                    lk=c.find('m:Link',NS)
                    if lk is not None and lk.text:
                        out.setdefault('links',[]).append((p,lk.text))
                    er=c.find('m:ExplicitRule',NS)
                    if er is not None and (er.text or '').strip():
                        out.setdefault('rules',[]).append((p,(er.text or '').strip()))
                    walk(c,p)
                else: walk(c,path_)
        walk(root,side)
    collect('INPUT'); collect('OUTPUT')
    out['links']=[{'target':t_, 'source':idmap.get(s,('?','?'+str(s)))[1]} for t_,s in out.get('links',[])]
    cm=r.find('m:ConstantMap',NS)
    out['constants']=[{'id':txt('ConstantID',c),'value':txt('Value',c)} for c in cm.findall('m:Constant',NS)]
    return out
if __name__=='__main__':
    d=dump(sys.argv[1])
    json.dump(d, open(sys.argv[2],'w'), indent=1)
    print(d['file'],'| clone-di:',d['desc'],'| links:',len(d.get('links',[])),
          'rules:',len(d.get('rules',[])),'constants:',len(d['constants']))
