# Il sorgente delle mappe: `.mxl`, `.map` binario e conversione

Com'e' fatta una mappa Sterling B2B Integrator in formato `.mxl`, dove si legge dal DB, come si converte dal `.map`
binario e come si crea o si modifica fuori dal Map Editor. Ricavato da mappe reali (flat posizionale, CSV, XML,
EDIFACT, X12) aperte, modificate e ricompilate nel Map Editor 8.0.3.0. Le regole di lavoro sono in `regole.md`; dove
qui c'e' scritto "da confermare in compilazione" il punto e' stato letto su file salvati dal Map Editor ma non provato
su tutti i casi.

## Sommario
- Dove sta il sorgente in Sterling
- Struttura del file
- ID e link (il punto piu' delicato)
- Nomi
- Regole estese: dove stanno, temporanei, indici, cicli, ProcessData, date, errori
- Input EDIFACT, attributi ed elementi foglia in output
- Leggere link e campi da un `.map` binario
- Forma del file: il Map Editor non e' un parser XML qualunque
- Conversione `.map` <-> `.mxl` con il Map Editor locale
- Come crearne una da zero o modificarla fuori dal Map Editor

## Dove sta il sorgente in Sterling

- `MAP` (`MAP_NAME`, `MAP_VERSION`, `UNCOMPILED_MAP`, `COMPILED_MAP`, `COMMENTS`, `DESCRIPTION`) ->
  `DATA_TABLE.DATA_OBJECT` con `DATA_ID = UNCOMPILED_MAP`: e' il sorgente **gzip**. Decompresso e' un `.mxl` (XML
  leggibile, namespace `http://www.stercomm.com/SI/Map`) oppure un `.map` binario ("GENTRAN TEMPLATE SOURCE").
  La versione predefinita sta in `MAP_VERSIONS.DEFAULT_VERSION` (in `MAP` la colonna non esiste).
- Il compilato (`.txo`) e' in `DATA_TABLE` con `DATA_ID = COMPILED_MAP`, anche lui gzip.
- Sterling esegue il `.txo`: un `.mxl` scritto o modificato a mano va **compilato** (Map Editor o `compila_mxl.py`)
  e caricato come `.map` + `.txo`.
- Per scaricare: `scripts\Export-SterlingSource.ps1 -Type Map` (sola lettura sul DB, decomprime il `DATA_OBJECT`).
  Per capire una mappa senza aprirla: `dump_mxl.py` (albero, regole) e `campi_link_mxl.py` (campi di output,
  tipo/formato, campo di input collegato); per controllarla prima del Map Editor: `controlla_mxl.py`.
- Nella maggior parte delle installazioni le mappe sono salvate come `.map` binario, che occupa molto meno del `.mxl`
  (ordine di grandezza: 0,8 MB contro 2,7 MB per una mappa grande): si converte in `.mxl` per lavorarci
  (§ Conversione).

## Struttura del file

```
<Mapper> <MapDetails> (VersionControl, Summary/Author/Description, Flags, EDIAssociations,
                       ExplicitRule/PreSessionRule facoltativa)
         <TemplateOption> <ExtendedRuleLibraries/>
         <INPUT>  <PosSyntax|XMLSyntax|EDISyntax|...> albero </...> </INPUT>
         <OUTPUT> <XMLSyntax|PosSyntax|...> albero </...> </OUTPUT>
```
- L'intestazione e' uguale tra mappe con sintassi diverse: la sintassi sta dentro `INPUT`/`OUTPUT`
  (`XMLSyntax` con `OutputFormat`, `EnableNamespaces`, `TrimPCData`, ...).
- `Summary/Description` e' il **nome interno** (il translation report lo stampa come "Map Name" e "Translation Object
  Name", e al check-in finisce in `MAP.DESCRIPTION`); `Summary/Author` e' l'autore.
- **Flat posizionale**: `Group` -> `PosRecord` -> `Field` con `StartPos` (da 0) e `Length`. Il tag del record sta in
  `BlockSig/Tag` con `TagPos`/`TagLength`.
- **XML**: ogni elemento e' un `XMLElementGroup` (`XMLTag`, `Min`/`Max`, `-1` = illimitato, `AllowAnyContent`,
  `PromoteGroup`). Un elemento con figli contiene un `XMLParticleGroup` (`ParticleType` `sequence` / `all` /
  `choice`). Un elemento semplice contiene un `XMLRecord` `_pcd_<nome>` (`RecordType` `pcdata`, `BlockSig` con
  `BlockType` 3) con un `Field` (`FieldType` `PCDATA`, `AttrType` `INVALID`). Gli attributi stanno in un `XMLRecord`
  `_attr_<elemento>` (`RecordType` `attribute`, `BlockType` 4) con `Field` `ATTRIBUTE`/`CDATA`.
- Gli elementi semplici hanno `PromoteGroup = yes`: i loro campi si leggono dal gruppo padre ripetuto (vedi indici).
  I contenitori hanno `PromoteGroup = no`.
- `ChildCount` = numero di figli diretti (gruppi, record, particle, campi).
- Tipo e formato del campo stanno in `StoreLimit` (`DataType` string/numeric/date, `MaxLen`, `Format`: `N0`, `R3`,
  `ISO-8601`, `YYYY-MM-DDTHH:MM:SS`...).

## ID e link (il punto piu' delicato)

- Ogni nodo (`Group`, `PosRecord`, `Segment`, `XMLElementGroup`, `XMLParticleGroup`, `XMLRecord`, `Field`) ha un
  `<ID>`, che deve solo essere **univoco**: il Map Editor li riassegna quando salva (dopo un taglia/incolla rinumera
  interi rami). Le mappe salvate dal Map Editor li hanno decrescenti nell'ordine del file, con la radice XML che ne
  consuma 3: e' lo schema da imitare quando si generano, ma non e' un vincolo.
- I collegamenti stanno **solo sui campi di output** (`<Link>`, subito dopo `</StoreLimit>`); il lato input non ha
  `Link`.
  - Input **posizionale**: `<Link>` = ID del `Field` di input.
  - Input **XML**: `<Link>` = ID del **record `_pcd_`** dell'elemento di input, non del campo. E' quello che il Map
    Editor scrive per ogni link creato a mano. Con i link sui `Field` la mappa si apre, ma il Map Editor non mostra i
    campi come collegati. `link_su_record_pcd.py` sposta i link sul record; `controlla_mxl.py` lo segnala.
  - Input **EDIFACT**: `<Link>` = ID del `Field` (anche per i temporanei).
- **Profondita'**: lo specchio dei temporanei deve stare allo stesso livello dell'output. Esempio anonimo: output
  `Root` -> `Item` -> campi: input `InputRoot` -> `TMP_Item` -> `TMP_*` (figlio diretto della radice). Output `Root`
  -> `Particle_1` -> campi: input `InputRoot` -> `TMP_Particle_1` -> `TMP_*`. Con una particle in piu' in mezzo
  (`InputRoot` -> `TMP_Particle_0` -> `TMP_Item`) il Map Editor non mostra i temporanei collegati; spostato il blocco
  di un livello, i link compaiono.
- Cose provate che **non** risolvono i link non mostrati: ID fuori ordine, radice con un solo ID, input rinumerato.
  Risolvono: livello giusto dello specchio e link sul record `_pcd_`.

## Nomi

- I nomi dei campi (e dei gruppi) devono essere **univoci per lato**: il Map Editor aggiunge `:2`, `:3` ai doppioni
  (es. `CompanyName` sotto un gruppo, `CompanyName:2` sotto un altro). Lo stesso nome puo' esistere in input e in
  output. Conta il `Name`; il tag XML vero sta in `XMLTag`/`Tag`.
- Nell'output XML i nomi sono univoci **per tipo di nodo**: elemento e campo foglia possono chiamarsi uguali.
- Nomi parlanti per temporanei e variabili: regola in `regole.md`.

## Regole estese

- Dove: `ExplicitRule` con `OnBegin`/`OnEnd` sui gruppi, `Rule`/testo di `ExplicitRule` sui campi,
  `PreSessionRule`/`PostSessionRule` in `MapDetails` (nel `.mxl` il testo e' XML-escaped: `&amp;`, `&lt;`, `&gt;`).
  Uno schema diffuso mette quasi tutta la logica in un `OnEnd` sulla radice dell'input, che scrive in **campi/gruppi
  temporanei** collegati all'output.
- **Flat**: temporanei = `PosRecord` in fondo all'input, scritti con `$INPUT.#campo = ...`.
- **XML**: la radice di input ha come figli `_attr_<radice>`, la particle dei dati e lo specchio dei temporanei, alla
  stessa profondita' dell'output (vedi "ID e link"). I temporanei sono una **copia della struttura dell'output**
  (stessi gruppi e campi con nome `TMP_` + nome nell'output, in una particle con `Min` 0), mai presenti nei dati; ogni
  campo di output e' collegato al suo gemello. L'output si ripete quante sono le istanze del gruppo temporaneo
  collegato.
- **Indici**: `$Gruppo[i1][i2]...#campo`, un indice per ogni livello sotto la radice, particle comprese, fino al
  gruppo nominato. Esempi (nomi anonimi): `$Item[1][idxItem].#OrderNumber` (particle radice, Item);
  `$ItemLocation[1][idxItem][1][1].#Notes` (particle radice, Item, particle di Item, ItemLocation); per lo specchio
  figlio diretto della radice `$TMP_Item[idxItem].#TMP_ObjectID`, `$TMP_Key[idxItem][1][1].#TMP_KeyValue`; campi al
  primo livello sotto la radice `$InputRoot.#TMP_System` (come `$INPUT.#campo` nel flat). Questi indici vanno
  **confermati in compilazione**. I nomi di gruppo con suffisso si scrivono cosi': `$partyLinks:9[...]`.
- Cicli: `idx = 1; while idx <= count($Item[1][*]) do begin ... idx = idx + 1; end` (vedi `regole.md` per
  `begin/end` e per `count()` che su un gruppo vuoto vale -1).
- **Commenti: solo `//`.** `/* ... */` da' `ERROR 1007 syntax error '/'` sulla riga del commento e poi errori a
  cascata (il testo del commento letto come codice: `'parola' has not been defined`, `syntax error 'else'`, `'END'
  without 'BEGIN'`).
- **Ciclo proprietario di un campo.** In compilazione il Map Editor elenca i cicli ("Compiling loop ..."): sono i
  gruppi con `PromoteGroup = no` o `Max` diverso da 1. Un gruppo promosso (`yes`, `Max` 1) non e' un ciclo e passa i
  suoi campi al ciclo sopra. Un campo si raggiunge dal suo ciclo: se il ciclo e' la radice, `$<radice>.#campo`; con
  `$TMP_gruppoPromosso[1][1].#...` (gruppo promosso sotto la radice) l'errore e'
  `ERROR 2001 'campo' is not a member of '<radice>'`. Sotto un ciclo ripetuto compila anche il riferimento dal gruppo
  promosso con indici (`$TMP_Key[idx][1][1]`). Stessa logica per i record Max 1 dentro un gruppo (`regole.md`).
- **ProcessData**: lettura `select xpathresult into var from processdata where xpath = "/ProcessData/.../text()";`
  (se non trova nulla la variabile resta `""`). Scrittura:
  `update ProcessData set XPathResult = sValore where XPath = "/ProcessData/OrderDate";`.
  L'xpath puo' essere costruito in una variabile:
  `aux = "/ProcessData/RESULT/ROW[Codice=" + #Codice + "][1]/Valore"; select xpathresult into aux from processdata where xpath = aux;`.
  Piu' valori sullo stesso percorso: `update ProcessData set xpathresult=#AAA where xpath="ROOT/ROW/AAA";` ripetuto
  accoda gli `AAA` nello **stesso** `ROW`; con prima `update ProcessData set xpathresult="" where xpath="ROOT/ROW/";`
  nasce un `ROW` nuovo per ogni valore.
- **Date**: `date("%Y-%m-%dT%H:%M:%S", stringa)` per l'XML, `date("%Y%m%d%H%M", ...)` per il flat;
  `new("java.util.Date")` per l'ora corrente; `object` per oggetti Java (es. `SimpleDateFormat`). Fuso orario con
  `SimpleDateFormat.setTimeZone(...)` (regola in `regole.md`). Ordinare i record: `sort($record,#campo);` /
  `sort($record,#campo desc);` nella OnEnd della radice di input.
- Funzioni frequenti: `trim`, `left`, `right`, `mid(s, da0, lunghezza)`, `aton`, `atoi`, `ntoa`, `count`, `strstr`,
  `strdate`. Elenco completo: `riferimento-ibm.md` § 2.
- **Errori**: bloccante `cerror(100, "messaggio", valore);`. Per **scrivere un messaggio nel report senza bloccare**
  la traduzione: costruire il testo (es. con `ntoa`) e usare un codice alto, es.
  `ntoa(nLength,sLength); sMsg = sLength + sHeight + sWidth; cerror(10005, sMsg);` (IBM classifica 10005 come
  Information). Condizioni: `&` e, `|` o, `!=`.
- **Insidia XML: `TrimPCData = 0` e spazi.** Lo spazio fra i tag istanzia i gruppi semplici con `Min` 0 anche se
  l'elemento non c'e': un `count()` su un gruppo facoltativo puo' contarlo (righe "fantasma"). Testare la presenza
  con il valore del campo, non con `count()` sul gruppo semplice. Se una regola esistente si appoggia a quella
  istanziazione, non attivare `TrimPCData` senza rileggerla.

## Input EDIFACT, attributi ed elementi foglia in output

Letti su mappe salvate dal Map Editor; da confermare in compilazione sul caso specifico.
- **Input EDIFACT** (`EDISyntax`): `Group` (nome `<numero>_<segmento>`, es. `3000_CNI`) -> `Segment` (`BlockSig/Tag`
  = codice del segmento) -> `Field` e `Composite` -> `Field`. L'ordine dei figli e' la posizione EDIFACT
  (`Element`/`SubElement` restano 0). Il Map Editor genera **tutto lo standard** con `Active` 0 sui segmenti e campi
  non scelti.
- `EDIAssociations_IN` (`AgencyID` E, `VersionID` es. `D 19B`, `VersionDescription`, `BindingID` es. IFTSTA). Se il
  Map Editor non ha la versione del partner, la struttura dei gruppi puo' essere diversa da quella della guideline
  (un segmento in un gruppo diverso, gruppi in ordine diverso): si ricostruisce l'input con i gruppi della guideline
  riusando le definizioni dei segmenti, e si confronta con `confronta_dizionario_edi.py`.
- **Temporanei in un input EDIFACT**: `Group` `TMP_...` (Min 0) sotto la radice con un `Segment` dal tag `$$$` (non
  compare mai nei dati); il `<Link>` del campo di output punta all'**ID del `Field`** temporaneo.
- **Indici EDIFACT**: `count($3000_CNI[*])`; segmento singolo dentro un gruppo -> nome del gruppo con un indice per
  ogni livello (`$3100_STS[iCNI][iSTS].#4405`); segmento ripetuto -> nome del segmento con un indice in piu'
  (`$RFF:2[iCNI][iSTS][iRFF].#1154:2`); temporanei `$TMP_Status[n].#campo`. Concatenazione di stringhe con `+`.
- **Attributi XML in output**: `XMLRecord` `_attr_<elemento>` primo figlio dell'elemento, `RecordType` `attribute`,
  `BlockSig/BlockType` 4; i campi hanno `FieldType` `ATTRIBUTE`, `AttrType` `CDATA`, `AttrBehavior` `IMPLIED` e il
  nome dell'attributo in `Tag`. I figli elemento stanno in un `XMLParticleGroup` `sequence` dopo il record.
- **Elemento foglia in output**:
  - l'elemento padre contiene un `XMLParticleGroup` `sequence` (PromoteGroup yes), che contiene un `XMLElementGroup`
    per ogni foglia;
  - la foglia ha Min 0, Max 1, `PromoteGroup` yes e `XMLTag` = nome;
  - nella foglia c'e' un `XMLRecord` `_pcd_<nome>`, con Min 1, Max 1, `BlockSig/BlockType` 3, `RecordType` `pcdata`
    e `Tag` = nome;
  - nel record c'e' un `Field` con lo stesso nome dell'elemento: `FieldType` `PCDATA`, `AttrType` `INVALID`,
    `AttrBehavior` e `Tag` vuoti, Mandatory yes;
  - ogni nodo consuma un ID.

## Leggere link e campi da un `.map` binario

Utile per controllare una copia senza il Map Editor (verificato confrontando un `.map` con la sua copia `.mxl`).
- Testo leggibile in Cp1252: nomi dei nodi e, in fondo, le regole estese (`OnBegin`/`OnEnd` e regole di campo come
  testo).
- Ogni nodo: 1 byte di tipo (`1F` particle, `1B` gruppo XML, `1C` record `_pcd_`, `1D` campo, `04` record
  posizionale, `06` campo posizionale), ID in 4 byte little-endian, 1 byte di lunghezza, nome.
- Campo posizionale di output: dopo nome e descrizione (anche lei con 1 byte di lunghezza) `01` + 7 byte, poi
  `StartPos` e `Length` (2 byte LE ciascuno), carattere di riempimento, `Mandatory` (0/1). Per i numerici
  `64 <decimali> 00 <01 = N, 00 = R>` (es. `64 02 00 01` = N2, `64 00 00 00` = R0); `73` = stringa.
- **Link**: sezione che inizia con `Link`. Subito dopo c'e' la **prima voce senza prefisso**: ID del nodo di input
  (il record `_pcd_` con input XML) + ID del campo di output, 4 byte LE ciascuno. Le voci successive sono `01 80` +
  ID input + ID output. Non c'e' un contatore dei link, e il byte subito dopo `Link` e' gia' il primo byte dell'ID
  di input: cercando solo le voci `01 80` si perde il primo link.

## Forma del file: il Map Editor non e' un parser XML qualunque

Un `.mxl` valido come XML ma serializzato con `xml.etree` di Python ha fatto chiudere il Map Editor in apertura
("Microsoft Visual C++ Runtime Library - Runtime Error!"), senza messaggi sulla causa. Differenze rispetto al file
salvato dal Map Editor:
- manca la dichiarazione `<?xml version="1.0" encoding="UTF-8"?>`;
- la radice non e' identica (`<Mapper VERSION="1.0" xmlns="http://www.stercomm.com/SI/Map" xmlns:xsi="...">`);
- elementi vuoti scritti `<Note />`: il Map Editor scrive `<Note></Note>` e usa `<X/>` solo per pochi tag
  (`UsageRelatedFieldName`, `NamespacePrefixes`, `ExtendedRuleLibraries`, `RepeatSuppressionChar`);
- ID: la radice XML dell'output ne consuma 3 (radice `n`, primo figlio `n-3`).

Quando si genera o si riscrive un `.mxl`: **modificare il testo** invece di riserializzare l'albero, oppure copiare
dichiarazione e tag radice dal file sorgente, serializzare gli elementi vuoti come li scrive il Map Editor, a capo
CRLF, e confrontare per ogni tipo di nodo la sequenza dei sotto-elementi con un file salvato dal Map Editor. Lo schema
ufficiale e' `Schemas\Mapper.xsd` nella cartella del Map Editor: `map2mxl.py` lo usa per validare.

## Conversione `.map` <-> `.mxl` con il Map Editor locale

Verificato sul Map Editor 8.0.3.0 (`C:\Program Files (x86)\Sterling Commerce\Map Editor`) su circa 180 mappe
(flat, CSV, XML, EDIFACT, X12; `.map` da 3 KB a 4,4 MB, il piu' grande da' un `.mxl` di 15,7 MB): tutte convertite e
valide per `Mapper.xsd` tranne 2 (vedi insidie).

**Riga di comando di `Mapper.exe`** (help `MapEditor.chm`)
- `mapper.exe -c <file o *.mxl>`: compila senza interfaccia e scrive il `.txo` accanto al sorgente. Dice solo
  "Impossibile compilare la mappa" senza il motivo; su un `.mxl` puo' non scrivere il `.txo` anche per una mappa che
  compila: usarlo sul `.map`, o usare `compila_mxl.py` che mostra anche gli errori con il numero di riga.
- `mapper.exe -s <tipo> <file>` ("salva come tipo di mappa"): per le mappe Sterling B2B Integrator (tipo 24) **non
  scrive niente**. **Non esiste un'opzione da riga di comando per convertire `.map` -> `.mxl`.**
- `-m` converte solo mappe Gentran Unix/iSeries/zSeries.

**Cosa funziona: pilotare "Salva con nome" da script** (`map2mxl.py`, Python + `pywinauto`). Si apre il `.map` con
`Mapper.exe <file>`, si manda il comando "Salva con nome" (ID MFC 57604), nel dialogo si sceglie il tipo `.mxl` e si
salva. Il risultato e' identico al salvataggio a mano (uniche differenze possibili nei caratteri di `SyntaxTokens`,
vedi sotto). Da 4 a 6 secondi per le mappe piccole, da 16 a 25 per le mappe EDI e split grandi.

**Al contrario, `.mxl` -> `.map` + `.txo`** (per il caricamento su Sterling). Lo stesso script, se riceve un `.mxl`,
salva come `.map` (il senso lo decide l'estensione del file passato); poi `mapper.exe -c <file>.map` scrive il `.txo`.
Andata `.map` -> `.mxl` e ritorno danno file **identici byte per byte** a quelli del "Salva con nome" manuale, e la
coppia `.map` + `.txo` prodotta cosi' e' stata caricata e traduce correttamente. Il `.map` e' deterministico (stesso
`.mxl` -> stesso `.map`), il `.txo` no.

**Insidie**
- `mapper.exe.manifest` chiede `highestAvailable`: con un utente amministratore il Map Editor parte elevato e uno
  script non elevato non riesce a pilotarlo (errore 740). Si lancia con la variabile d'ambiente
  `__COMPAT_LAYER=RunAsInvoker`, che vale solo per quel processo e non cambia nessuna impostazione.
- **`mapper.exe -c` con il percorso completo del file puo' non scrivere il `.txo`**: esce con codice 0 e non compila
  (a volte con la finestra "Unable to load map '<percorso>.map'"). Funziona lanciandolo con la cartella della mappa
  come directory di lavoro e il solo nome del file (`Start-Process -WorkingDirectory <cartella>` o
  `ProcessStartInfo.WorkingDirectory`, argomenti `-c <nome>.map`). Se il `.txo` manca, riprovare cosi' prima di
  concludere che la mappa non compila.
- Per le mappe molto grandi compare l'avviso "Questa mappa contiene un numero molto elevato di oggetti ... salvare
  utilizzando il formato `.MAP`": **OK** salva comunque in `.MXL`. Poi c'e' una finestra di avanzamento da aspettare.
- In `SyntaxTokens` i caratteri oltre ASCII sono scritti come `0xFF`, `0xDF`, `0xA1`, `0xA3` oppure come carattere
  (`ÿ`, `ß`, `¡`, `£`) a seconda di chi ha salvato: e' lo stesso valore, non una modifica della mappa.
- **Il titolo del dialogo "Salva con nome" cambia con il PC** (puo' chiamarsi `Save As` anche con Windows in
  italiano): lo script riconosce il dialogo dal campo nome file (id 1148) e dal combo del tipo (id 1136), uguali in
  ogni lingua.
- Ogni tanto (circa 1 volta su 180, di solito al primo avvio) il click su Salva non arriva: lo script ripreme Salva
  dopo 5 s e, se non basta, rifa' la conversione con un processo nuovo (riga `RIPROVO`); se si ferma ancora, il
  messaggio elenca le finestre aperte del Map Editor.
- Qualche mappa (es. una JSON con userexit molto grande) fa andare in crash il Map Editor al salvataggio in `.mxl`
  ("Microsoft Visual C++ Runtime Library ... Runtime Error!"): e' un limite del Map Editor su quella mappa; in quel
  caso lavorare nel Map Editor.
- Un processo Map Editor separato per ogni mappa, chiuso alla fine: le finestre aperte dall'utente non vengono
  toccate. Durante la conversione non toccare la finestra che si apre.
- Il `.txo` non serve per confrontare due sorgenti: due compilazioni della stessa mappa differiscono in centinaia di
  byte (indirizzi di memoria). Per sapere se due mappe si comportano uguale si traducono gli stessi file con
  entrambe; per un controllo grezzo si confrontano le stringhe (segmenti, XPath, costanti) del `.txo` decompresso.

## Come crearne una da zero o modificarla fuori dal Map Editor

1. Partire da una mappa esistente con la stessa sintassi di output (e se possibile di input): copiare intestazione e
   `OUTPUT` tali e quali, cosi' l'output verso il sistema a valle resta identico.
2. Costruire l'`INPUT` dall'XSD o dal tracciato con i blocchi descritti sopra; nomi univoci.
3. Aggiungere i temporanei (specchio dell'output, particle `Min` 0), scrivere la regola, collegare i campi di output
   ai temporanei.
4. ID univoci, `Link` sul record `_pcd_` del temporaneo gemello (input XML), specchio alla stessa profondita'
   dell'output; verificare con `controlla_mxl.py`: XML valido, nessun ID duplicato, `ChildCount` coerenti, nessun
   link orfano; confrontare l'albero di input con l'XSD.
5. Compilare (`compila_mxl.py` o Map Editor), provare in TEST con file reali, leggere lo status report della
   Translation (`regole.md`, "Errori: dove guardare").
