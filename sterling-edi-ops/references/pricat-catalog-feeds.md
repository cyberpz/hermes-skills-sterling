# Pricat / catalog feed per partner marketplace (Amazon X-BUY e simili)

## When to Use
Quando un partner/marketplace (marketplace buy-out, outlet, ecc.) manda un template di pricat da riempire e serve una query ad hoc sull'anagrafica prodotto perché non esiste un feed pronto.

Classe di lavoro: il partner manda un template xlsx con una sola colonna popolata (`SKU taglia`); le altre colonne vanno riempite con una query ad hoc sull'anagrafica, eseguita in sola lettura (SELECT-only) sul DB del master.

## Struttura SKU moda a concatenazione (pitfall generale)

- Formato tipico: `modello + tessuto + colore + taglia` concatenati, nessun separatore.
- Il prefisso stile (modello+tessuto+colore) può avere **lunghezza variabile** (es. 19 **o** 20 caratteri a seconda della lunghezza del colore).
- **Pitfall: mai fare split a posizione fissa o troncare gli ultimi N caratteri per ottenere la taglia** — con prefisso a lunghezza variabile una quota degli SKU (anche ~12%) viene corrotta a colore/taglia. Verificare sempre l'ipotesi sui dati prima di scrivere la query: contare le uguaglianze `SKU_taglia == Model||Fabric||Color||Size` e guardare la distribuzione delle lunghezze dei prefissi.
- Strategia corretta: estrarre il codice modello con `SUBSTR(sku,1,N)` solo se N è certo, interrogare l'anagrafica per stili con le taglie reali, e matchare il suffisso dello SKU template contro le taglie vere dell'anagrafica — non per posizione.
- Taglie: check size-scales miste (letterali + numeriche) e **separatori decimali misti nella stessa colonna** (`4.5` e `4,5` coesistono). Normalizzare il separatore prima di ogni match o confronto.

## Procedura

1. Leggere il template senza dipendenze: `scripts/xlsx_dump_stdlib.py <file.xlsx> [sheet]` (TSV su stdout, risolve sharedStrings e inlineStr).
2. Ipotesi sulla struttura → verifica numerica (uguaglianze di concatenazione, distribuzione lunghezze) → solo poi scrivere la query.
3. Liste distinte da estrarre: modelli (prefisso certo, → IN list) e stili. Chunk delle IN a 999 valori (limite Oracle).
4. Bozza SELECT in sola lettura (su DB vecchi: ROWNUM, niente PIVOT); colonne in output = header del template. Tabella anagrafica sconosciuta → query di scoperta su `ALL_TAB_COLUMNS` filtrata per owner.
5. Esecuzione della SELECT da parte di chi ha accesso al DB → CSV → riempimento del template (scrittura xlsx via openpyxl; la lettura non la richiede).

## Convenzioni template marketplace (esempio X-BUY)

- Un foglio per categoria, header a riga 1, più un foglio Summary/pivot.
- Colonne tipiche: Year, Season, Gender, Model, Fabric, Color, SKU (con underscore), SKU+taglia (compatto), Size, Currency, Wholesale price, Tot Units, Tot Cost, RRP, Delivery Code, Composizione tessuto, Linelist, Nome modello, Made in/out, Gruppo colore, Colore stile, External Product ID Type (`EAN`), External Product ID, Delivery Window.
- `SKU` con underscore e `SKU+taglia` compatto sono due formati diversi dello stesso stile: non riconciliarli per lunghezza, ma per componenti (modello, tessuto, colore, taglia).
