"""Controlli su un sorgente di mappa Sterling (.mxl) prima di aprirlo nel Map Editor.

Uso: python -I controlla_mxl.py <mappa.mxl> [--strict]

Errori (la mappa non si apre bene o perde i link):
- XML non valido;
- <ID> duplicati;
- <Link> di un campo di output verso un ID che non esiste nell'input;
- input XML: <Link> verso un Field invece che verso il record _pcd_ (il Map Editor non mostra il link);
- due gruppi/record, o due campi, con lo stesso nome sullo stesso lato (il Map Editor li rinomina con :2, :3);
  gruppo e campo con lo stesso nome sono normali (elemento XML semplice);
- regola estesa oltre 65535 caratteri (viene tagliata).
Avvisi:
- regola estesa oltre il 90% del limite; indentazione o allineamenti fatti con spazi invece che con TAB;
- ChildCount diverso dal numero di figli diretti;
- commenti /* */ nelle regole estese (nella mappa non sono accettati: solo //);
- temporanei TMP_ dentro un gruppo/particle con Min diverso da 0 (Mandatory Block Missing);
- Description del Summary diversa dal nome del file (nome interno rimasto da una copia);
- Author del Summary diverso dall'autore atteso secondo la convenzione del team: --autore VALORE, altrimenti
  ricavato dall'utente Windows se ha la forma nome.cognome (iniziale + cognome, maiuscolo); se l'utente non ha
  quella forma e manca --autore, il controllo non si fa;
- campo dell'input scritto in una regola (riga non commentata) ma non collegato a nessun campo di output:
  il valore non esce nel file (se e' voluto, commentare la riga).
Uso completo: python -I controlla_mxl.py <mappa.mxl> [--strict] [--autore VALORE]
Regole: regole.md e formato-mxl.md di questa skill.
"""
import collections
import os
import re
import sys
import xml.etree.ElementTree as ET

M = '{http://www.stercomm.com/SI/Map}'
NODES = ('Group', 'Segment', 'Composite', 'PosRecord', 'VarDelimRecord', 'ODBCOutputRecord', 'XMLElementGroup', 'XMLParticleGroup', 'XMLRecord', 'Record', 'Field')


RULE_LIMIT = 65535   # limite di una regola estesa (64 KB): oltre, la regola viene tagliata


def tag(e):
    return e.tag.replace(M, '')


# Regole estese: OnBegin/OnEnd dei gruppi, Rule, regole di sessione e <ExplicitRule> dei campi (la regola estesa
# di un Field sta come testo in <ExplicitRule>; quella di MapDetails e' solo un contenitore con figli, senza testo).
RULE_TAGS = ('OnBegin', 'OnEnd', 'Rule', 'PreSessionRule', 'PostSessionRule', 'ExplicitRule')


def is_rule(e):
    return tag(e) in RULE_TAGS and bool(e.text and e.text.strip())


def rule_owner(r, parent):
    """Nome del nodo a cui appartiene la regola: il padre se ha <Name> (Field con ExplicitRule), altrimenti il nonno."""
    for owner in (parent.get(r), parent.get(parent.get(r))):
        if owner is not None and owner.findtext(f'{M}Name'):
            return owner.findtext(f'{M}Name')
    return 'mappa'


def expected_author():
    """Autore atteso: --autore XXX, altrimenti dall'utente Windows nome.cognome -> iniziale+cognome; None se non ricavabile."""
    if '--autore' in sys.argv:
        i = sys.argv.index('--autore')
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1].strip().upper()
    user = os.environ.get('USERNAME', '')
    if '.' in user:
        first, last = user.split('.', 1)
        if first and last:
            return (first[0] + re.split(r'[.\s_-]', last)[0]).upper()
    return None


def spaces_to_tab(text):
    """Caratteri che si risparmiano scrivendo con TAB indentazione e allineamenti (sequenze di 2+ spazi fuori dalle stringhe)."""
    spare = 0
    for line in text.split('\n'):
        inq, run = False, 0
        for ch in line:
            if ch == '"':
                inq = not inq
            if not inq and ch == ' ':
                run += 1
                continue
            if run > 1:
                spare += run - 1
            run = 0
    return spare


def main(path, strict=False):
    errs, warns = [], []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as ex:
        print('ERRORE XML non valido:', ex)
        return 1
    parent = {c: p for p in root.iter() for c in p}

    ids = collections.Counter(e.findtext(f'{M}ID') for e in root.iter() if tag(e) in NODES)
    errs += [f'ID duplicato: {i} ({n} volte)' for i, n in ids.items() if i and n > 1]

    sides = {}
    for side in ('INPUT', 'OUTPUT'):
        s = root.find(f'.//{M}{side}')
        if s is None:
            errs.append(f'manca la sezione {side}')
            continue
        sides[side] = s
        # univoci tra i gruppi/record e tra i campi (un elemento XML semplice ha gruppo e campo con lo stesso nome);
        # i Composite EDI no: lo stesso composito standard (C507, C002...) sta in piu' segmenti col suo nome
        names = collections.Counter(('campo' if tag(e) == 'Field' else 'gruppo', (e.findtext(f'{M}Name') or '').strip())
                                    for e in s.iter() if tag(e) in NODES and tag(e) != 'Composite')
        errs += [f'{side}: nome di {k[0]} ripetuto {n} volte: {k[1]!r}' for k, n in names.items() if k[1] and n > 1]
        for e in s.iter():
            if tag(e) in NODES and tag(e) != 'Field':
                cc = e.findtext(f'{M}ChildCount')
                if cc is not None:
                    real = sum(1 for c in e if tag(c) in NODES)
                    if int(cc) != real:
                        warns.append(f"{side}: ChildCount {cc} ma {real} figli in {e.findtext(f'{M}Name')!r}")

    if 'INPUT' in sides and 'OUTPUT' in sides:
        inp = sides['INPUT']
        by_id = {e.findtext(f'{M}ID'): e for e in inp.iter() if tag(e) in NODES}
        xml_in = inp.find(f'{M}XMLSyntax') is not None
        for f in sides['OUTPUT'].iter(f'{M}Field'):
            link = f.findtext(f'{M}Link')
            if not link:
                continue
            tgt = by_id.get(link)
            nm = f.findtext(f'{M}Name')
            if tgt is None:
                errs.append(f'OUTPUT {nm!r}: Link {link} non punta a niente nell\'input')
            elif xml_in and tag(tgt) == 'Field' and tag(parent[tgt]) == 'XMLRecord':
                errs.append(f'OUTPUT {nm!r}: Link {link} sul Field: con input XML va sul record _pcd_ '
                            f'{parent[tgt].findtext(f"{M}ID")} (vedi link_su_record_pcd.py)')
        for e in inp.iter():
            if tag(e) in NODES and (e.findtext(f'{M}Name') or '').startswith('TMP_'):
                p = e
                while p in parent and tag(parent[p]) in NODES:
                    p = parent[p]
                    mn = p.findtext(f'{M}Min')
                    if mn not in (None, '0') and not (p.findtext(f'{M}Name') or '').startswith('TMP_') \
                            and tag(p) == 'XMLParticleGroup':
                        warns.append(f"temporaneo {e.findtext(f'{M}Name')!r} dentro {p.findtext(f'{M}Name')!r} "
                                     f"con Min {mn}: con Min diverso da 0 il translator puo' dare Mandatory Block Missing")
                        break

    longest = (0, '')
    for r in root.iter():
        if not is_rule(r):
            continue
        oname = f'{rule_owner(r, parent)} [{tag(r)}]'
        if '/*' in r.text:
            warns.append(f"commento /* */ in una regola estesa ({oname}): nella mappa usare //")
        n = len(r.text)
        if n > longest[0]:
            longest = (n, oname)
        if n > RULE_LIMIT:
            errs.append(f'regola estesa {oname}: {n} caratteri, oltre il limite di {RULE_LIMIT}: viene tagliata')
        elif n > RULE_LIMIT * 0.9:
            warns.append(f'regola estesa {oname}: {n} caratteri, oltre il 90% del limite di {RULE_LIMIT}')
        spare = spaces_to_tab(r.text)
        if spare:
            warns.append(f'regola estesa {oname}: indentazione/allineamento con spazi, con i TAB si risparmiano '
                         f'{spare} caratteri (tabify_regole.py)')
    # Campi dell'input scritti da una regola ma non collegati a nessun campo di output: il valore non esce.
    # Se e' voluto, la riga nella regola si commenta (//) e qui non viene contata (regole.md).
    if 'INPUT' in sides and 'OUTPUT' in sides:
        # solo assegnazioni: l'istruzione comincia con il campo ($gruppo[..].#campo = / #campo =); nelle regole
        # '=' e' anche il confronto (if $x.#Qual = "CNE" then), che non va contato
        assign = re.compile(r'^(?:\$[\w:]+(?:\[[^\]]*\])*\.)?#([A-Za-z_]\w*(?::\d+)?)\s*=(?!=)')
        scritti = collections.Counter()
        for r in root.iter():
            if is_rule(r):
                prev = ''
                for line in r.text.split('\n'):
                    code = line.split('//', 1)[0]
                    # riga che continua una condizione (la precedente finisce con | & ( or and): e' un confronto
                    cont = re.search(r'(\||&|\(|\bor|\band)\s*$', prev) is not None
                    for stmt in re.split(r';|\bthen\b|\belse\b|\bbegin\b|\bdo\b', code):
                        s = stmt.strip()
                        m = assign.match(s)
                        if m and not cont and s.count(')') <= s.count('('):
                            scritti[m.group(1)] += 1
                        cont = False
                    if code.strip():
                        prev = code.rstrip()
        in_fields = {}
        for f in sides['INPUT'].iter(f'{M}Field'):
            in_fields.setdefault(f.findtext(f'{M}Name'), f)
        linked = {f.findtext(f'{M}Link') for f in sides['OUTPUT'].iter(f'{M}Field') if f.findtext(f'{M}Link')}
        for nome, n in sorted(scritti.items()):
            f = in_fields.get(nome)
            if f is None:
                continue
            fid, rid = f.findtext(f'{M}ID'), parent[f].findtext(f'{M}ID')
            if fid not in linked and rid not in linked:
                warns.append(f"campo {nome!r} scritto in una regola ({n} volte) ma non collegato all'output: il valore "
                             f"non esce nel file. Collegarlo, oppure commentare la riga se e' voluto")

    if longest[0]:
        print(f'regola estesa piu\' lunga: {longest[1]} {longest[0]} caratteri su {RULE_LIMIT} '
              f'({longest[0] * 100 // RULE_LIMIT}%)')

    author = (root.findtext(f'.//{M}Summary/{M}Author') or '').strip()
    expected = expected_author()
    if expected and author.upper() != expected:
        warns.append(f'Summary/Author = {author!r}: atteso {expected!r} (convenzione del team, vedi --autore; '
                     f'Map Editor, Modifica > Dettagli > Autore)')

    desc = (root.findtext(f'.//{M}Summary/{M}Description') or '').strip()
    base = re.sub(r'([._](PROD|TEST))?([._]v\d+)?([._](PROD|TEST))?$', '', os.path.splitext(os.path.basename(path))[0])
    if desc and desc != base:
        warns.append(f'Summary/Description = {desc!r}, file = {base!r}: controllare il nome interno della mappa')

    for w in warns:
        print('AVVISO', w)
    for e in errs:
        print('ERRORE', e)
    print(f'{len(errs)} errori, {len(warns)} avvisi')
    return 1 if errs or (strict and warns) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], '--strict' in sys.argv))
