"""Riscrive le regole estese di un sorgente .mxl con i TAB al posto degli spazi di indentazione e allineamento.

Uso: python -I tabify_regole.py <mappa.mxl> [<uscita.mxl>]   (senza uscita scrive <mappa>.tab.mxl)

Regola (regole.md di questa skill, "Regole estese"): le regole estese hanno un limite di 65535
caratteri; l'indentazione si fa con un TAB per livello e gli allineamenti con un TAB, mai con sequenze di
spazi. Dentro le stringhe ("...") non cambia nulla; gli spazi singoli tra le parole restano (un TAB costa uguale).
Stampa la lunghezza di ogni regola prima e dopo. Il file va poi controllato con controlla_mxl.py e compilato.
"""
import os
import re
import sys

LIMIT = 65535


def tabify(text):
    out = []
    for line in text.replace('\r\n', '\n').split('\n'):
        line = line.rstrip()
        m = re.match(r'^([ \t]*)(.*)$', line)
        ind, body = m.group(1), m.group(2)
        width = 0
        for ch in ind:
            width = (width // 4 + 1) * 4 if ch == '\t' else width + 1
        tabs = '\t' * (width // 4) + ('\t' if width % 4 else '')
        res, inq, i = [], False, 0
        while i < len(body):
            c = body[i]
            if c == '"':
                inq = not inq
                res.append(c)
                i += 1
                continue
            if not inq and c in ' \t':
                j = i
                while j < len(body) and body[j] in ' \t':
                    j += 1
                res.append('\t' if (j - i) > 1 or body[i] == '\t' else ' ')
                i = j
                continue
            res.append(c)
            i += 1
        out.append(tabs + ''.join(res))
    return '\n'.join(out)


def unesc(s):
    return s.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&apos;', "'").replace('&amp;', '&')


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def main(src, dst):
    data = open(src, encoding='utf-8').read()
    pat = re.compile(r'<(OnBegin|OnEnd|Rule|PreSessionRule|PostSessionRule)>(.*?)</\1>', re.S)

    def repl(m):
        old = unesc(m.group(2))
        if not old.strip():
            return m.group(0)
        new = tabify(old)
        flag = '  OLTRE IL LIMITE' if len(new) > LIMIT else ''
        print(f'{m.group(1):8} {len(old):6} -> {len(new):6} caratteri (limite {LIMIT}){flag}')
        return f'<{m.group(1)}>{esc(new)}</{m.group(1)}>'

    out = pat.sub(repl, data)
    open(dst, 'w', encoding='utf-8', newline='').write(out)
    print('scritto', dst)


if __name__ == '__main__':
    s = sys.argv[1]
    main(s, sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(s)[0] + '.tab.mxl')
