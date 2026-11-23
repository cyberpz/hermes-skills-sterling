# Riferimento IBM per le mappe (Map Editor / translator, B2B Integrator 6.2.0)

**A cosa serve.** Da aprire solo quando, lavorando su una mappa, si incontra una funzione o keyword di
extended rule, una standard rule, una proprieta' o un messaggio d'errore che non si conosce. Riassume
la documentazione IBM **6.2.0** (pagine aggiornate da IBM nel 2026); non sostituisce le regole del team.

**Come usarlo.** Cercare la voce (Grep su nome della funzione, codice d'errore, nome della
proprieta'), leggere solo quella sezione; per il dettaglio aprire la pagina IBM nel browser:
**URL = `https://www.ibm.com/docs/en/b2b-integrator/6.2.0?topic=` + il `topic` indicato**
(es. `reference-accum` -> `...6.2.0?topic=reference-accum`).

**Prima valgono le regole della skill.** Convenzioni di lavoro (temporanei `TMP_`, indici XML, commenti `//`,
`begin/end`, TAB e limite 64 KB delle regole, `aton` vs `atoi`, ProcessData, Java/`SimpleDateFormat`, property
del translator, best practice IBM): `regole.md` e `formato-mxl.md` di questa skill. Qui solo cio' che li' non c'e'.

**Nota sulla fonte.** Nella copia locale delle pagine IBM le `[ ]` degli indici sono andate perse
(`$GROUPNAME011` = gruppo con tre indici). Qui la sintassi e' scritta con le `[ ]`, come la descrive
`translator-introduction-indexes`.

## Sommario

1. Extended rule: struttura, tipi, scope, ordine di esecuzione
2. Funzioni e keyword (tabella A-Z)
3. Date e ore nelle regole
4. Operatori, simboli, indici, parole riservate, regole non supportate
5. Select / update nelle regole
6. User exit (Java) e librerie di extended rule
7. Standard rule
8. Proprieta' dei campi
9. Proprieta' di record, gruppi, file e mappa
10. Compile error
11. Messaggi del Map Editor
12. Codici del translator report
13. Translation service
14. Per formato
15. Pagine IBM chiave / non trattati qui

## 1. Extended rule: struttura, tipi, scope, ordine di esecuzione

- **Struttura** (`rules-about-extended`): dichiarazioni (solo se servono) poi istruzioni, ognuna chiusa
  da `;`; **le condizioni di `if` e `while` no**.
- **Nomi di variabile**: lettere, cifre, `:` e `_`, non iniziano con una cifra, **case sensitive**. I
  campi della mappa non si dichiarano.
- **Tipi**: `integer`, `real`, `string[n]`, `datetime`, array (`integer a[10];`), `object`. **`char`
  non esiste** (un carattere e' una `string`).
- **Il translator non inizializza le variabili** (indici compresi): inizializzarle sempre. In Map
  Details c'e' *Initialize Extended Rule Variables* (§ 9).
- **Scope** (`rules-about-extended-rule-processing`, `rules-defining-session-rule`):
  - *Pre-session* (Edit > Session Rules): gira prima della traduzione, variabili **globali**.
    *Post-session*: gira dopo, nessuno scope permanente.
  - *On Begin / On End*: una volta **per occorrenza**; le variabili dell'On Begin valgono fino all'On
    End e nei figli.
  - *Regola di campo*: dura quanto il campo, gira **dopo** la standard rule.
- **Storage interno costruito sulla struttura dell'input**: dal lato output una regola vede **solo il
  record corrente e l'input**; dal lato input vede tutto. Per riempire l'output si scrive sul lato
  input di un link (temporanei linkati, `regole.md`). Errori tipici 2010, 2037 (§ 10).
- **Ordine** (`processing-input-rule`, `processing-output-rule`): input: per ogni gruppo con dati On
  Begin -> per campo standard rule poi extended rule -> On End. Output: per ogni record con dati On
  Begin (al primo record del gruppo) -> regole di campo -> formattazione del campo -> scrittura ->
  On End a fine gruppo.
- Asterisco sull'icona = componente con regola. Nell'editor: *Compile*, doppio clic sull'errore porta
  alla riga.

## 2. Funzioni e keyword (tabella A-Z)

Indice: `rules-alphabetical-language-reference`; keyword vs comandi:
`rules-extended-rule-keywords-commands` (keyword di controllo: `begin`, `end`, `break`, `continue`,
`if...then...else`, `while...do`). **topic di ogni voce = `reference-<nome>`** (`ifthenelse`,
`whiledo`), salvo dove indicato.

**Nomi di altri linguaggi -> funzione Sterling** (per il Grep): substring / substr -> `mid`; indexOf / instr /
contains -> `strstr`; length -> `len`; string to number / parseInt -> `atoi` / `aton`; number to string -> `ntoa`;
date format / formatDate -> `strdate`; concatenazione -> `concat`; trim spazi -> `trim` (vedi insidia);
for / loop -> `while...do`; lookup tabella -> `select`.

| Nome | Sintassi | Cosa fa | Insidia (dalla pagina) |
|---|---|---|---|
| `accum` | `x = accum(n);` `accum(n) = v;` | Legge/scrive l'accumulatore `n` della standard rule Use Accumulator | Si usa il **numero**, non il nome |
| `atoi` / `aton` | `i = atoi(s);` `r = aton(s);` | Stringa -> integer / real | |
| `begin` / `end` | `begin ... end` | Corpo di `if`/`else`/`while` con piu' istruzioni | |
| `break` | `break;` | Esce dal `while` piu' interno | |
| `call` | `call lib.regola(p1, p2)`; `i = call lib.regola p1` | Regola di una extended rule library (§ 6) | topic `erl-calling-rule-from-extended-rule-library-in-map` |
| `cerror` | `cerror(cod, $G[..].#campo, "testo");` / `cerror(cod, "testo");` | Errore di compliance nel translator report | **Solo lato input**. La pagina dice il 3o parametro sia opzionale sia obbligatorio (anche vuoto). La forma a 2 parametri e' in `codes-xml-messages` (nata per SWIFTNet). Codici § 12 |
| `collate` | `collate($MASTER, #m1 ASC, ..., $DETAIL, #d1, ..., $RESULT);` | Lega due gruppi non gerarchici tramite campi chiave: sposta il dettaglio in un gruppo risultato **figlio del master**, stessa struttura di campi | Prima `sort` di entrambi nello stesso ordine; dopo, i dati del dettaglio **non ci sono piu'**; stesso numero di chiavi; dati grandi -> out of memory |
| `concat` | `concat(s1, s2, n);` | Accoda a `s1` i primi `n` caratteri di `s2` | |
| `continue` | `continue;` | Passa al giro successivo del ciclo | |
| `count` | `n = count($G[*]);` | Iterazioni di un gruppo o record ripetuto | **Gruppo vuoto -> -1**, non 0. Un solo `[*]` per regola (2103) |
| `date` | `date(a,m,g[,h,mi])`, `date("fmt", s)` | Crea un datetime (§ 3) | Mese 1-12. Formato errato o `""` -> -1000 ms prima del 1/1/1970, **nessun errore in compilazione** (`expressions-date-syntax`) |
| `delete` | `delete($G[n]);` | Cancella l'occorrenza `n` | |
| `empty` | `empty($G[..].#campo);` | Campo a **null** (diverso da `""` o 0) | |
| `eof` | `i = eof(0);` | 1 = input finito, 0 = altri dati | Argomento diverso da 0 -> eccezione |
| `exist` | `if exist($G[..].#campo) then`; `exist($gruppo)` | Diverso da 0 se il campo ha dati | Forma col solo gruppo **solo XML** (elemento presente senza figli valorizzati); accetta anche `%record` |
| `get` / `set` | `i = get days(d);` `set days(d, i);` | Legge / imposta years, months, days, hours, minutes, seconds | |
| `getcurrentlocationindex` | `s = getcurrentlocationindex();` | Livello e iterazione correnti (`01:01:02`) | Utile con `messagebox` per il debug dei cicli |
| `if...then...else` | `if c then ... else ...` | 0 = falso, altro = vero; annidabile | Niente `;` dopo la condizione |
| `index` | `index(n)` | Iterazione corrente del ciclo al livello `n` | |
| `left` / `right` | `left(s, n)` / `right(s, n)` | Primi / ultimi `n` caratteri | |
| `len` | `i = len(s);` | Numero di caratteri | |
| `messagebox` | `messagebox("testo", 0);` | Scrive nel **tx.log** del server | Lo `0` e' obbligatorio |
| `mid` | `mid(s, inizio, n)` | `n` caratteri da `inizio` | **Base zero** |
| `new` | `ob = new("pkg.Classe", arg);` | Oggetto Java (§ 6) | topic `code-creating-object` |
| `ntoa` | `ntoa(r, s);` | Real -> stringa nel 2o argomento | |
| `numerrors` | `i = numerrors();` | Errori nel report al momento della chiamata | |
| `occurrencetotal` | `occurrencetotal(%record)` | Occorrenze del record processate finora | `$gruppo` solo XML; azzerare con `resetoccurrencetotal(%record);` |
| `readblock` | `readblock(s)` | Legge il blocco successivo (segmento/record) senza compliance | **Solo posizionale ed EDI**. Restituisce 0 anche a ogni a-capo: fine file con `eof(0)`. Usato con Document Extraction |
| `select` | `select campo into var from tab where k = e and ...;` | Legge dati di Sterling (§ 5) | Nomi diversi da quelli della standard rule |
| `sort` | `sort($G, #f1 ASC, #f2 DESC);` | Ordina le istanze nello storage (default ASC) | Avanzata (indici); dati grandi -> out of memory |
| `strdate` | `strdate(d, "fmt", s);` | Datetime -> stringa (§ 3) | |
| `strstr` | `i = strstr(s, sotto);` | Posizione della prima occorrenza | **Base zero**; -1 se assente |
| `sum` / `sumtotal` | `sum();` `sum("n");` / `r = sumtotal(#campo);` | Somma progressiva del campo su cui gira `sum` (`"n..."` = somma come negativo) / la legge | |
| `trim` / `trimleft` / `trimright` | `trim(s)`, `trim(s, "z")` | Toglie spazi (default) o il carattere indicato | **`trim(s, " ")` non e' valido** per gli spazi; carattere case sensitive |
| `unreadblock` | `unreadblock();` | Riporta indietro di un blocco l'input (e i contatori) | **Una volta sola**, dopo `readblock`; non XML |
| `update` | `update tab set c = e, ... where k = e;` | Scrive in Sterling (§ 5) | Transaction Register: in memoria fino alla `select` |
| `while...do` | `while c do begin ... end` | Test prima di ogni giro | Niente `;` dopo la condizione |
| `writeblock` | `writeblock(s);` | Scrive la stringa come blocco, senza compliance | Solo posizionale ed EDI; con `readblock` sostituisce i wildcard segment |

Voci dell'indice IBM: 44 (piu' `call` e `new`, documentate a parte). Esempi:
`rules-common-statements-examples`, `examples-conditional-logic` (confronto stringhe con `=`, `<`, `>`),
`examples-numeric-functions`, `examples-data-block-functions-readblock-unreadblock-writeblock`.

## 3. Date e ore nelle regole

- `date(a,m,g[,h,mi])`, `date("fmt", s)`, `time(h,mi[,s])`; `strdate` per la stringa
  (`expressions-date-syntax`, `examples-datetime-expressions`).
- **`<<`** aggiunge un intervallo: `d = #Data << days(5);` con `years`, `months`, `weeks`, `days`,
  `hours`, `minutes`, `seconds`.
- Format specifier (`date-format-specifiers`, ripetuti in `reference-strdate`): `%Y` `%y` anno 4/2
  cifre, `%m` mese, `%d` giorno, `%H` ora 00-23, `%I` 01-12, `%M` minuti, `%S` secondi, `%j` giorno
  dell'anno (`%j%y` bisestile), `%a`/`%A` giorno della settimana, `%b`/`%B` mese in lettere, `%w`
  0-6 (domenica 0), `%U`/`%W` settimana (domenica/lunedi' primo giorno), `%%`. Solo in
  `date-format-specifiers`: **`%8` = ISO-8601** `YYYYMMDD'T'HHMMSS'.'sssZ`, **non combinabile**. Solo in
  `strdate`: `%D` centesimi di secondo.
- Data corrente in un campo: standard rule System Variable (§ 7). Fusi orari: `regole.md`.

## 4. Operatori, simboli, indici, parole riservate, regole non supportate

- **Operatori** (`symbols-operators`): `+` (somma e concatenazione), `-`, `*`, `/`, `=` (assegnazione
  **e** uguaglianza), `>`, `<`, `>=`, `<=`, `!=`, `!` not, `&` and, `|` or, `<<` date.
- **Simboli** (`operators-symbol-syntax`): costante `"..."`; `#CAMPO`; `$GRUPPO.#CAMPO`;
  `$GRUPPO[i1][i2].#CAMPO` (dal livello esterno); campo ripetuto con un indice in piu' sul campo; array
  per elemento (`a[0]`..`a[4]`); `accum(n)`. Nuove istanze solo di componenti dello storage interno.
- **Indici** (`translator-introduction-indexes`): formato completo `$Gruppo[i]...#Campo` col **gruppo
  ripetuto piu' interno** e un indice per livello; formato breve `#Campo` **solo** in regole di campo o
  di record sul record corrente; da regole di gruppo e di sessione sempre il formato completo. In XML
  ogni elemento e content particle conta come gruppo, `1` per quelli che non ripetono
  (`euixff-how-use-index-elements-content-particles-that-do-not-repeat`,
  `format-why-were-these-errors-received`). Esempi pratici: `formato-mxl.md` § Regole estese.
- **Parole riservate** (`rules-other-reserved-words`): REF, INTEGER, REAL, STRING, CHAR, DATETIME,
  STOP, GOTO, PRINT, INPUT, NEWLINE, YEARS, MONTHS, WEEKS, DAYS, HOURS, MINUTES, SECONDS, TIME, INTO,
  FROM, WHERE, INSERT, VALUES, AND, WINEXEC, EXEC, FTELL, FSEEK, CURRENT, READBYTES, WRITEBYTES, OBJECT,
  CREATEOBJECT, DELETEOBJECT, QUERYOBJECT, GETIID, OUT, BYTEVECTOR, SLEEP, PARAMCOUNT, PARAM, SETPARAM,
  AUDITLOG, NEW, CLASS, INSTANCEOF, STATIC, ASC, DESC, LONG, SUM, SUMTOTAL, OCCURRENCETOTAL, CALL,
  FUNCTION, RETURN, RESETOCCURRENCETOTAL, FINDOBJECTNAME.
- **Regole Gentran non supportate** (compile error; `rules-other-unsupported-extended`,
  `information-extended-rules`): INSERT, AUDITLOG, WINEXEC, CREATEOBJECT, DELETEOBJECT, QUERYOBJECT,
  GETIID, BYTEVECTOR, EXEC, PARAM, PARAMCOUNT, SETPARAM; readbyte/writebyte e wild block ->
  `readblock`/`writeblock`; fseek/ftell -> `unreadblock`.

## 5. Select / update nelle regole

`rules-select-update-available-options`. **Solo dati di Sterling**, nessun database applicativo
(`information-select-update-standard-rules`).

| Tabella | select | update | Campi |
|---|---|---|---|
| `CODELIST` (trading partner code list) | si' | - | DESCRIPTION, NAME (nome lista), RECEIVERCODE, SENDERCODE, TEXT1-TEXT4 |
| `PROCESSDATA` | si' | si' | XPATH, XPATHRESULT |
| `CORRELATIONDATA` | - | si' | NAME, VALUE (coppia univoca per documento) |
| `DOCUMENTEXTRACTION` | - | si' | EDISTANDARD, ACCEPTERLOOKUPALIAS, RECEIVERID, SENDERID |
| `ENVELOPE` (Generic Envelope) | si' | - | PARM, VALUE |
| `TRANSACTIONREGISTER` | si' | si' | FIELD1-FIELD6 (lunghezze § 7) |

Esempi ProcessData: `formato-mxl.md` § Regole estese.

## 6. User exit (Java) e librerie di extended rule

- **Oggetti** (`exits-about-user`, `exits-using-data-types`): `object ob; ob = new("pkg.Classe", arg);`,
  metodo `ob.metodo(p)`, proprieta' `ob.prop` in lettura e scrittura (`code-getting-property-value`,
  `code-setting-property-value`). Tipi: integer=int, real=double, datetime=java.util.Date,
  string=java.lang.String, object=java.lang.Object; conversione fallita -> regola interrotta ed errore
  nel report.
- Il Map Editor **non controlla** metodi e proprieta' in compilazione; i loro risultati non si possono
  confrontare (tipo ignoto). Eccezioni e wrapper: `regole.md` § Best practice IBM. La classe vuole un costruttore con
  argomento stringa. Keyword **`long`** dopo un parametro = intero a 64 bit (default 32).
- Di solito oggetto dichiarato e creato nella pre-session (`exits-location-within-map`). User exit che
  dipendono dal JDK: **ritestarle a ogni upgrade o fix pack** (`rules-user-exits`).
- **Extended rule library** (`editor-extended-rules-library`): file `.erl` di regole riusabili, risorsa
  versionata con check-in. Usata **in compilazione, non a runtime** (nel `.txo` solo le regole usate):
  cambiata una regola, **ricompilare** le mappe che la usano (elenco:
  `merl-viewing-list-maps-that-use-extended-rule-library`). Una sola libreria per nome in una mappa
  (l'ultima con check-in). Variabili globali in libreria solo con "Text Substitution", sconsigliato.
  Il nome nella `call` e' quello del file senza versione (`SWIFT_2006.erl` -> `SWIFT`).

## 7. Standard rule

Una sola per campo, gira prima dell'extended rule (`editor-using-standard-rules`). Limiti gia' in
`regole.md` § Best practice IBM (Constant, System Variable, Accumulator, Select max 8 campi).

| Standard rule | Cosa fa / note | topic |
|---|---|---|
| **Use Constant** | Copia una costante (Map Constants). Con un *qualifier*: se il qualifier non viene generato, la costante non si scrive. Una costante si puo' riempire da extended rule ma si usa solo con questa rule | `rules-using-use-constant-standard-rule` |
| **Use Code** | Valida contro una code list salvata **nella mappa** (*Raise compliance error*) e/o copia la descrizione in un campo. Lista generica alternativa: trading partner code list senza sender/receiver | `rules-using-use-code-standard-rule`, `rule-standard-tab-use-code` |
| **Use Accumulator** | Fino a 6 operazioni per campo su primario/alternativo: increment, decrement, sum (con segno), hash sum (valore assoluto), load, use, zero, multiply, divide e modulo (due versi), negate, move/add/multiply/divide/modulo con l'alternativo. Per sottrarre: negate + sum | `accumulator-operations` |
| **Loop Count** | Giri del ciclo corrente o di uno esterno | `rules-using-loop-count-standard-rule` |
| **System Variable** | Data e ora correnti; solo campi Date/Time | `rule-configure-system-variable-standard` |
| **Select** | Da Document Envelope, Trading Partner Code List (receiver o sender code, nome esatto), **Process Data** (XPath, es. `trackingIdentifier/text()`), Transaction Register. Synonym Table **non supportata**. In input vede il gruppo corrente, in output il record corrente | `rules-using-select-standard-rule`, `rule-process-data-select-standard` |
| **Update** | Verso Document Extraction, Process Data (XPath + XPath Result), Correlation Data (cercabile da Correlation Search), Transaction Register, Transaction XREF | `rules-using-update-standard-rule`, `rule-correlation-data-update-standard` |
| **Transaction Register** | Controllo duplicati: Update carica Field1-6 in memoria, la Select **successiva** controlla e, se nuovo, inserisce; duplicato = errore nel report. Lunghezze: Field1 150, Field2-5 35, Field6 30 (oltre: troncato). Traduzione fallita = riga non inserita | `rule-transaction-register-select-standard`, `rule-field-size-limits` |

Le standard rule non corrette non vengono eseguite (`information-select-update-standard-rules`).

## 8. Proprieta' dei campi

Tab **Validation** (`sbimep-validation-tab`): mandatory, *not used*, lunghezza min/max, data-type
(String, Number, Date/time, Bin Data/Bin Length solo con segmento EDI "Binary", Length prima di Data),
formato, byte raw (endian), Positive Number Format.

- **Number** (`fields-using-number-field`): `N0-N9` decimale **implicito** (2.01 in N2 = `201`; con
  meno decimali completa a destra: `1` in N3 = .001); `R0-R17` decimale **esplicito** fino a x cifre,
  **tronca gli zeri finali** (3.10 in R2 = `3.1`); Overpunch0-9; Packed0-9 (solo posizionale,
  property `datatype.PackedDecimal` per zSeries).
- **Zeri finali** (`fields-truncating-number-when-converting-strings-numbers`): oltre alle property in
  `regole.md` § Best practice IBM, la mappa ha **Keep Trailing Zeros** in Map Details (Never / Always / Use Setting from Translator
  properties). Nelle property per mappa il nome e' la **Description** di Map Details.
- **BigDecimal** (`fields-big-decimal-bigdecimal-support-real-numbers`): di default il translator usa
  il `double` Java, con errori di arrotondamento (esempio IBM: 80000.01 x 100 = 8000000.999999999).
  Per mappa: **Use BigDecimal Mode** in Map Details. Property: `storage.bigDecimalRoundingMode`
  (default HALF_UP; CEILING, FLOOR, UP, DOWN, HALF_DOWN, HALF_EVEN, UNNECESSARY),
  `storage.bigDecimalMaximumDefaultScale` (default 10), `extendedRules.useRoundingModeForDoubles` da
  mettere a false con BigDecimal (la pagina lo scrive una volta senza la `s` finale).
- **Date/Time** (`fields-specify-datetime-field`): tra gli altri `YYYYMMDD`, `DDMMYYYY`, `YYMMDD`,
  `YYYY-MM-DD`, `HHMM`, `HHMMSS`, `HH:MM:SS`, giuliani (`YYDDD`, `YYYYDDD`), mese in lettere
  (`DDMMMYYYY`), `ISO-8601` (`YYYYMMDDTHHMMSS.mmmZ`), `YYYY-MM-DDTHH:MM:SS`, **`XSDTIME`**
  (`YYYY-MM-DDTHH:MM:SS.sss+-HH:MM`, frazioni e fuso opzionali): in input data+ora, solo ora o solo
  data; **in output sempre data e ora**. Formati custom su ogni postazione (`regole.md`); utility per esportarli
  e riapplicarli: `fdif-upgrade-utility-that-extracts-reapplies-custom-date-formats`.
- **String** (`fields-using-string-field`): formato = **syntax token** (caratteri ammessi, controllati
  in compliance) o **Free Format** (nessun controllo). Token: `field-creating-syntax-tokens`.
- **Segno `+`** (`fields-using-plus-sign-in-number-field`): campo (Validation > Positive Number Format:
  Use properties file setting / Don't allow / Allow) > default per i campi nuovi (Preferences >
  Standard Formats) > property (`regole.md` § Best practice IBM). Nelle property per mappa gli **spazi della Description vanno
  preceduti da `\`**, poi riavvio (`field-disable-in-single-map`). Insidie
  (`upsinf-caveats-allowing-generating-plus-sign-in-numeric-fields`): campo lungo abbastanza per il
  `+`; in EDIFACT il `+` del dato va preceduto dal release character (in output lo mette il
  translator). Non per campi SQL e packed.

## 9. Proprieta' di record, gruppi, file e mappa

**Map Details** (Edit > Details, `properties-map-details`): *Author* e *Description* obbligatori,
Description **univoca** (il translator identifica la mappa con questa); *Map Function* = Sterling B2B
Integrator; *Use Configurable Trimming* (input posizionale: toglie i pad secondo l'allineamento,
sinistra -> da destra, destra -> da sinistra, centro = default -> entrambi; serve a conservare spazi);
*Use BigDecimal Mode*; *Initialize Extended Rule Variables*; *Keep Trailing Zeros*; *Throw an error if
a field is present but marked as "Not Used"*; *Major/Minor version* 0-255 solo informativi; *EDI
Associations*.

**Looping** (`sbimep-looping-tab-1`, `sbimep-looping-tab`): Min usage 0 = condizionale, >=1 =
obbligatorio; Max usage. *Promote records to parent*: alla compilazione porta i figli nel padre, **solo
per sottogruppi a iterazione singola** (quando l'output non e' raggruppato). Max 1 non si splitta ne'
promuove (`basics-splitting-groups`, `basics-promoting-groups`). *Get usage from related field* (solo
input): ripetizioni prese da un campo intero di un segmento precedente, non ripetuto, nello stesso
gruppo. Normal / Loop Start / Loop End (EDI). XML: Conditional/Mandatory e Can (not) repeat / max usage
(`properties-repeating-tab`).

**Tag**: posizionale Tag, Position, Length (`sbimep-tag-tab-1`); delimitato Tag + *Field #*
(`sbimep-tag-tab-3`); EDI codice segmento (`sbimep-tag-tab`); XML nome elemento (inizia con lettera,
`_` o `:`), *Allow ANY content* (dopo, nessun figlio/pcdata/attributo mappato), *Defined as abstract*
da **togliere** per compilare (`sbimep-tag-tab-4`). Tag per formato e record senza tag: `regole.md`.

**Segmento EDI, Special** (`properties-special-tab`): Normal; **Wildcard** (passa senza elaborazione
come un campo solo: il primo campo deve avere Max Length pari al segmento intero; con cautela);
**Floating** (posizione non fissa); Binary; *Alternate Tag* (uscita da un ciclo di wildcard).

**Ordering** (solo input, `properties-ordering-tab`): Normal / Start-Inside-End random order con
*Ordering Tag* uguale per la sequenza (in EDI automatico: `100_NM1` -> `100`, `REF:2` -> `REF`); non
per XML. Inizio o fine mancante: errori 20746/20747.

**Conditions** (`properties-conditions-tab`): Paired, Required, Exclusion, Conditional, List
Conditional. **Solo da guardare**: modificarle genera errori di compliance.

**Key field** (`sbimep-key-field-tab-input-side-map`): riconosce il record se un campo vale una
costante/code list o coincide con un campo di un record precedente (fino a 3); *Match record when key
does not match*. **Solo stringhe** (su numerici risultato non garantito).

**Posizionale**: Record tab (`properties-record-tab`) Record Length + fino a 2 Record Delimiters.
Comportamento (`memi-differences-between-sterling-b2b-integrator-translator-thesterling-gentranserver-translator`):
solo Length -> legge quei byte **ignorando gli a-capo**; Length + Delimiters -> si ferma al
delimitatore; solo Delimiters -> fino al delimitatore. Position tab (solo input,
`properties-position-tab`): start, lunghezza, pad, allineamento. Settings: carattere decimale
(`properties-settings-tab`).

**XML**: Settings, *Handling whitespace in PCDATA* (Always / Never / property); default input =
property, output = Never; `trimPcdata=false` in customer_overrides per non togliere gli spazi in input
(`documents-managing-pcdata`; insidia `TrimPCData`: `formato-mxl.md`).
Output tab (`properties-output-tab`): prolog / doctype (Public/System ID), a capo e indentazione,
**Encoding**. Namespace: `documents-using-namespaces-in-xml-file`; `EnableNamespaces` va confrontato tra le versioni: `regole.md`.

**Encoding** (`properties-encoding-tab`): se in Sterling e' impostato l'encoding del documento di
input, **prevale su quello della mappa**; quello dell'output viene dalla mappa (Translation service).

**Repeat tab** (composite e campi EDI, `properties-repeat-tab`): min/max, *Treat this field as a
repeating field* con max 0 o 1.

## 10. Compile error

Elenco completo: `messages-compile-error`. Dopo un errore spesso seguono errori a cascata: correggere il
primo e ricompilare (`regole.md`).

| Codice | Testo chiave -> cosa fare |
|---|---|
| 1000 / 1003 / 1008 | manca `.` tra gruppo e campo / `,` tra parametri / `#` davanti al campo |
| 1001 / 1006 | regola vuota / corpo di `if`, `else`, `while` vuoto |
| 1002 | fine inattesa: regola incompleta |
| 2000 | group ... undefined: gruppo inesistente o non raggiungibile (esempio in `regole.md`, record Max 1) |
| 2001 | ... is not a member of ...: campo non del gruppo/ciclo indicato (esempi: `formato-mxl.md` § Regole estese) |
| 2002 / 2003 | indici insufficienti / troppi |
| 2004 | ... has not been defined: variabile non dichiarata |
| 2005 | out of temporary variables: spezzare l'espressione |
| 2008 | field type unknown: dare il data-type al campo |
| 2009 | campo locale senza gruppo corrente (regola di sessione): indirizzo completo |
| 2010 | instances ... are transient: indirizzo completo su un gruppo di **output** (vale solo per l'input) |
| 2011 | manca il riferimento al campo |
| 2037 | Output fields can only be referenced in field extended rules: scrivere sull'input e linkare |
| 2100-2102 | array: non e' array / indice richiesto / overflow |
| 2103 / 2104 | un solo `[*]` per regola / `[*]` richiesto |
| 2200 / 2201 | stringa attesa / string overflow (destinazione piu' corta) |
| 3000-3004 | dichiarazioni: dimensione, `]`, nome mancanti |
| 3005 | nome gia' definito nello stesso scope |
| 3006 / 3007 | numero di accumulatore non valido |
| 4000-4011 | espressioni: numerica, termine, operatore, `(` `)`, tipo errato (4007), relazionale (4008), argomento mancante (4009), assegnazione (4010), secondo operando (4011) |
| 4100-4102 | data o modificatore di data attesi |
| 5000-5005 | THEN / DO / END / IF / FROM / INTO attesi |
| 5006 | END without BEGIN |
| 5018 / 5019 | troppi / pochi parametri |
| 20001 | campo data senza formato |
| 20003-20006 | standard rule: costante, code list, qualifier o campo descrizione inesistenti |
| 20007 / 20008 / 20030 | key field con costante/code list inesistente, o inattivo |
| 20700-20702 | binari: un solo Bin Length e Bin Data, Length prima, entrambi presenti |
| 20703 | gruppo senza figli attivi |
| 20704-20715 | attributi XML: enumerazione senza Use Code, code list o default non validi, character reference, `<` nel default |
| 20746 / 20747 | random order senza Start o End |

Il `1007 syntax error '/'` dei commenti `/* */` (`regole.md`) non e' nella tabella IBM.

## 11. Messaggi del Map Editor

Elenco completo: `messages-sterling-b2b-integrator-map-editor-error`. I piu' utili:
- *...cannot be linked because the input field is deeper than the output field*: link solo tra campi
  dello stesso livello.
- Nomi non univoci: campo nel gruppo padre, gruppo o record.
- *A group or record with a maximum usage of 1 cannot be split or promoted*; Max usage >0 e >= Min.
- *Element ... was defined as abstract*: togliere il flag o usare un elemento concreto.
- *You must type a description / the name of the author*: Map Details incompleto.
- Limiti: 6 voci per Use Accumulator, 8 campi per Select.
- *Standard Rule Select Data Missing* (Select Transaction Register senza Update prima); *Standard Rule
  Duplicate Transaction Register Error* (duplicato).
- Incolla rifiutato: es. struttura XML in un posizionale.
- Colonna SQL con caratteri non ammessi: nei nomi di campo solo `a-z A-Z 0-9 _ :`.
- Map Test: *Bad Response 404* (URL), *SSL Error* (Use SSL incoerente o certificato non nel JRE).
- Memory/Resource Exception, system error in compilazione: spazio disco, riavvio.

## 12. Codici del translator report

Indice `reference-compliance-codes`; sono anche i codici di `cerror`.

**Generali** (`codes-general-messages`). Error: 100 MandatoryDataMissing, 101 InsufficientRepeats, 102
TooManyRepeats, 110 IncorrectDataFormat, 111 DataNotMinLength, 112 DataExceedsMaxLength, 113
InvalidDate, 120 TooManyComponents, 121 TooManyCompositeElements, 122 UnsupportedDataType, 123
DataConversionError, 140 StandardRuleFailure, 142 StandardRuleUseCodeDataMissing, 143
StandardRuleDataConversionError, 170 ExtendedRuleFailure, 171 ExtendedRuleDataConversionError, 300
MandatoryBlockMissing, 301 MandatoryGroupMissing, 316 MaxUsageExceeded, 400/401 Block/Field
ProcessorInitializationFailure. Warning: **25 BlockDataUnknown** (blocco che non combacia con nessun
record attivo: § 14 EDI e `regole.md`). Information: 12-21 (tempi, blocchi letti/scritti, nome del
translation object) e **10001-10018** (BlockSignature, BlockCount, BlockName, FieldName, **10005
FieldData**, Exception, GroupName, FieldId, FieldNumber, Instance, RuleType, OnBeginRule, OnEndRule,
RepeatCount, BlockData, BlockSignatureIDTag, MapIterationCount, AdditionalInformation); 10002-10004,
10016, 10017 solo con `cerror` in una regola **di campo**. L'uso di `cerror(10005, ...)` per un
messaggio non bloccante e' in `formato-mxl.md`: IBM classifica 10005 come Information.

**SQL** (`codes-sql-messages`). Error: 700 DataSourceOpenError, 701 DataSourceRollback, 702
CommitError, 703 RollbackError, 710 QueryOpenError, 711 CommandError, 712 CursorError, 713
GetFieldError, 721 OutputOperationError, 722 PreparedStatementError. Information: 724
UpdateEffected0Rows, 725/726 RetryingAsInsert/AsUpdate, 10700-10705 (data source, pool, query,
statement, cursor, column).

**EDI** (`codes-edi-messages`), Information: 103 IllegalRepeatingDelimiter, 104
IllegalSubElementDelimiter, 105 ElementPosition, 106 SubElementPosition.

**XML** (`codes-xml-messages`). Error: 610 XMLParticleORGroupError, 690 XMLParserError, 691
XMLElementUnknown, 692 XMLPcDataUnknown, 693 XMLAttributeUnknown. Information: 10060-10066 (PublicId,
SystemId, LineNumber, ColumnNumber, Message, XMLTagName, XMLNamespaceURI).

**Voci del report** (`report-error-codes`): *Map Iteration Count* (riesecuzioni della mappa sul batch),
*Block Name* (nome univoco, es. `REF:3`), *Block Count*, *Field Number*, **Location Index** = iterazione
di tutti i gruppi fino al record, separata da `:` (`22:03:01`; `0` alla radice). Dove si legge il
report: `regole.md` (§ Errori: dove guardare).

## 13. Translation service

`adapters-translation-service`. Sostituisce il primary document col risultato; mappa **con check-in e
abilitata**. Stato Success / Error (dettaglio nel translator report).

| Parametro | Significato |
|---|---|
| `map_name` | Mappa |
| `exhaust_input` | Yes = riesegue la mappa fino a fine input (ogni segmento deve combaciare con un record attivo, in ordine); No = una esecuzione |
| `ErrorIfAllDataNotConsumed` | Errore se resta input (solo senza `exhaust_input`); default false |
| `ErrorIfNoOutput` | Errore se l'output e' vuoto; default false |
| `validate_input` / `validate_output` | Validazione contro i lati della mappa |
| `validate_input_against_dtd` | No / DTD / XML schema |
| `output_report_to_process_data` / `output_to_process_data` | Report / output (solo XML) nel ProcessData |
| `useStreams` | Streaming per file grandi, default Yes |
| `edi_input_*` / `edi_output_*` | Delimitatori EDI (tag, segment, element, sub_element, repeating_element, release_character, decimal_separator), letti anche dal contesto del BP |
| `FromSchema` / `ToSchema` (solo BPML) | Cambio del prefisso di schema nelle mappe SQL (case sensitive, coppie separate da `@`, `ToSchema` vuoto toglie lo schema) |
| `sql_statement_use_batching`, `sql_statement_maximum_batchsize` (solo BPML) | Batch SQL: non per record con retry, serve *Use Transaction* e un DB che lo supporti |

## 14. Per formato

- **EDI / EDIFACT** (`documents-about-edi-data-format`, `documents-create-edi-layout-from-edi-standard`):
  layout dallo standard, attivi solo i componenti obbligatori. Segmento ricevuto ma non attivo ->
  **warning 25**; i segmenti non attivi restano e possono dare errori di lunghezza
  (`documents-activate-map-components`). *Auto Trim* attiva i componenti da un file di esempio
  compliant, senza envelope se la mappa non li ha (`trim-auto-rules`). Delimitatori e opzioni di output
  *Suppress leading zero* (0.25 -> .25) / *Pad with leading zero* (`documents-verify-edi-delimiters`).
  **UNA** solo come *syntax record* del file di input, mai come segmento
  (`documents-set-up-syntax-record-edifact-una-segment`). LS/LE:
  `documents-using-loop-start-loop-end-segments`. Livelli **HL** con accumulatori (esempio IBM X12 856):
  `editor-hierarchical-levels-hl-in-maps`. Struttura del `.mxl` EDIFACT: `formato-mxl.md`.
- **XML** (`documents-about-xml-data-format`, `format-xml-components`): XML 1.0 con piccole estensioni
  (ripetizioni). Layout da DTD/XSD solo con schema valido e MSXML (`format-xml-considerations`).
  Componenti: root (non linkabile), element, content particle (choice/sequence/all), pcdata (uno per
  elemento), attribute container, attribute. Indici § 4. XML Encoder object `.ltx`
  (EDI/posizionale/delimitato -> XML senza mapping): `map-compile-xml-encoder-object`.
- **Posizionale** (`documents-about-positional-data-format`): record e gruppi prima dei campi; Record
  Length/Delimiters e Configurable Trimming § 9; spazi iniziali:
  `mcd-preserve-leading-spaces-when-mapping-positional-data-format`.
- **Delimitato** (`documents-about-variable-length-delimited-data-format`): un record per riga (CRLF o
  LF); ogni campo delimitato anche se vuoto; campo col delimitatore tra virgolette; **numero di campi
  nel file = esattamente quello del record**. Layout da file:
  `mvldd-create-variable-length-delimited-layout-from-delimited-file`.
- **SQL** (`documents-about-sql-data-format`, `mapping-how-translator-works-sql-maps`,
  `documents-considerations-sql-mapping`, `properties-data-sources-tab`): DSN = nome del pool JDBC di
  Sterling; *Use Transaction* = rollback se errori (con pool locale e `no_rollback_on_validation_error`
  non a true); pool `local` consigliato (rollback deciso dal translator), `remote` lo decide il DB.
  `commit_after_map_iteration=true` (translator.properties) per commit a ogni iterazione;
  `sql.noRollbackOnValidationError`. In input **niente parametri alla query**; in output niente result
  set; ogni Output Record con almeno una colonna TableKey; data source separati se SQL su entrambi i
  lati; copia/incolla sul lato SQL perde i link. Output Record: Insert/Update/Delete con retry
  insert<->update (`properties-sql-operation-tab`). Outbound: colonna flag per i record processati.
- **CII, COBOL copybook**: fuori ambito (`editor-mapping-cii-documents`,
  `editor-create-map-using-cobol-copybook`).

## 15. Pagine IBM chiave / non trattati qui

Chiave: `rules-alphabetical-language-reference`, `rules-about-extended-rule-processing`,
`translator-introduction-indexes`, `operators-symbol-syntax`, `rules-select-update-available-options`,
`editor-using-standard-rules`, `accumulator-operations`, `editor-sterling-b2b-integrator-map-properties`
(indice di tutti i tab di proprieta'), `properties-map-details`, `sbimep-validation-tab`,
`messages-compile-error`, `messages-sterling-b2b-integrator-map-editor-error`,
`reference-compliance-codes`, `adapters-translation-service`, `map-compile` (`.txo` mai sopra il
sorgente, nome senza spazi ne' apostrofi, `.mxl` richiede MSXML),
`maps-performance-tuning-when-translating-very-large-files` (file da 5 GB o molti livelli di ciclo:
`maxKeyFileSize` in customer_overrides).

Non trattati qui (questo riferimento copre EDIFACT/X12, XML, posizionale, delimitato, SQL): SWIFT/SWIFTNet,
Fedwire, CHIPS, ACH, HIPAA, SPEC2000, CII, COBOL, WTX, TRADACOMS, NCPDP, migrazione da Gentran
(synonym table, TDF/DDF/IFD).
