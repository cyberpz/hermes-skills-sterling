# Regole per scrivere e correggere mappe Sterling B2B Integrator

Regole generali, ricavate da casi reali su mappe in produzione e dalla documentazione IBM. Leggerle **tutte** prima
di scrivere o correggere una mappa. Se il team ha convenzioni proprie (prefissi dei nomi, autore, commenti), quelle
prevalgono dove sono indicate come "convenzione del team". Come e' fatto il `.mxl`: `formato-mxl.md`; funzioni,
proprieta' e codici d'errore IBM: `riferimento-ibm.md`.

## Sommario
- Input
- Output XML
- Una traduzione vede un file solo
- Chiamate esterne e userexit
- Nomi e regole estese
- Struttura del sorgente `.mxl` (temporanei e link)
- Lunghezza dei campi e tag dei record
- Errori: dove guardare
- Versioni e passaggio TEST -> PROD
- Best practice IBM (Map Editor)

## Input

- **Buste EDI: sapere se la mappa le riceve.** Quando nel flusso il deenvelope (EDIFACT `UNA`/`UNB`/`UNH`/`UNT`/`UNZ`)
  avviene prima della traduzione, l'input della mappa parte dal primo segmento del messaggio (es. `BGM`) e finisce con
  l'ultimo prima di `UNT`: la mappa non prevede i segmenti di busta e nel Test del Map Editor i file di prova vanno
  usati **senza busta** (con `UNH`/`UNT` dentro il test fallisce). Controllare come e' fatto il flusso (BP) prima di
  aggiungere o togliere segmenti di busta.
- **Mappa EDI: il dizionario dell'input deve essere la versione che manda il partner.** Se la mappa nasce da un'altra
  (es. clonata da una D09A e il partner manda D01B), confrontare **segmento per segmento** le definizioni dell'input
  con quelle della versione del partner (composite ed elementi nell'ordine, lunghezze, tipi) e allineare: se un
  elemento cambia posizione, vanno spostati i campi e corrette le regole estese che li usano; aggiornare anche
  `EDIAssociations_IN` (`VersionID`, `VersionDescription`). Le definizioni si prendono da una mappa gia' in produzione
  con la stessa versione (stesso directory = stessi segmenti anche se il messaggio e' diverso). Attenzione: anche le
  mappe di riferimento possono avere lunghezze personalizzate. Script: `scripts\confronta_dizionario_edi.py`.
- **Split di un file flat: la stessa regola estesa, cambia solo la condizione che chiude il pezzo.** Le mappe di split
  usate con `DocumentExtractionService` (`DocExtractMapList`) non traducono: ricopiano righe. Input posizionale con
  un gruppo (Min 1, Max 1), output con un solo record finto; la logica e' la regola estesa del campo che contiene la
  riga:

  ```
  string[1024] sBuffer;
  readblock(sBuffer);             // la riga su cui si e' fermata la split
  writeblock(sBuffer);            // va nel pezzo in uscita
  while readblock(sBuffer) do     // righe successive
  begin
  	if <condizione di fine pezzo> then
  	begin
  		unreadblock();          // la riga torna nell'input: aprira' il pezzo dopo
  		break;
  	end
  	writeblock(sBuffer);        // altrimenti la riga si aggiunge al pezzo
  end
  ```

  - **Una riga per pezzo**: condizione sempre vera (`len(sBuffer)>=0`); in input basta un record con un campo, senza
    tag significativo.
  - **Testata con le sue righe** (testata `01` + dettaglio `02`): condizione `mid(sBuffer,0,2)="01"`, il pezzo si
    chiude all'arrivo della testata successiva; in input un gruppo con `Header` tag `01` (Max 1) e `Detail` tag `02`
    (Max 9999), ognuno con un campo lungo quanto la riga.
  - La lunghezza del campo nel record non limita la riga copiata, che passa per `readblock`; il limite e' la
    dimensione del buffer (`string[1024]`: righe piu' lunghe non verificate).
  - La mappa che riceve i pezzi deve avere gli stessi record della split: con una split a riga singola su un file con
    righe di dettaglio, la riga di dettaglio arriva da sola e la mappa successiva va in errore (es. `Invalid Date`).
- **Input XML: un elemento che la mappa non conosce non la fa fallire.** La mappa legge il file dall'alto in basso;
  un elemento che non c'e' nella struttura di input viene cercato fino in fondo all'albero, non trovato e ignorato. Il
  dato si perde in silenzio e la traduzione puo' finire bene (anche con un output vuoto) oppure dare errori che
  sembrano di ciclo. Nel report resta solo un **warning** `Code: 691 Unrecognized XML Element` con il nome
  dell'elemento; `Contains errors ?` vale `false`. `AllowAnyContent=no` non cambia questo comportamento. Quindi:
  (1) ogni elemento nuovo del tracciato va aggiunto anche all'input della mappa; (2) nel BP che traduce, se serve,
  leggere il report (`Status_Rpt('Report')`) e mandare in errore se contiene `Unrecognized XML Element` o
  `Contains errors ? true`, invece di fidarsi dell'esito del servizio `Translation`.
- **EDIFACT in ingresso con caratteri accentati: il partner deve mandare UTF-8 (`UNB+UNOY:3` o `UNOW:4`), e la
  codifica dell'input della mappa (`CharacterEncoding`) resta vuota.** Osservato in produzione: Sterling passa i byte
  del file cosi' come sono nell'XML di output (`UTF8`); con `UNOC` (ISO 8859-1) la `ñ` arriva a valle come `?`, e
  impostare `ISO8859_1` sull'input non risolve (esce U+FFFD). Nel primo test cercare un carattere accentato
  nell'output.
- **Input posizionale a righe: nel Record tab impostare anche i Record Delimiters, non solo la Record Length.** Con la
  sola Record Length il translator legge quel numero di byte ignorando gli a-capo: con righe di lunghezza diversa (o
  CRLF contati come dati) i record si spostano. Con Length e Delimiters si ferma al delimitatore, che ha la
  precedenza. Fonte: IBM 6.2.0, topic `memi-differences-between-sterling-b2b-integrator-translator-thesterling-gentranserver-translator`.

## Output XML

- **Nell'XML prodotto da noi i dati vanno in elementi, non in attributi** (convenzione consigliata). Si scrive
  `<ReportNumber>65588</ReportNumber>`, non `<Report ReportNumber="65588">`: con gli attributi l'XML e' piu' difficile
  da leggere nelle verifiche (ProcessData, documenti, mail di errore). Un campo senza valore non viene scritto: chi
  legge l'XML deve trattare l'elemento assente come NULL o vuoto. Gli attributi restano solo se li impone un tracciato
  del partner. Struttura di un elemento foglia nel `.mxl`: `formato-mxl.md`.
- **`EnableNamespaces` va confrontato a ogni nuova versione.** Se il servizio a valle legge i campi solo nel loro
  namespace, con i namespace disattivati riceve un messaggio vuoto e puo' scartarlo senza errore visibile nel BP
  (risposta 200 compresa). Il flag (sezione `OUTPUT` del sorgente) puo' cambiare senza volerlo anche in una modifica
  che tocca solo le extended rule: confrontarlo con la versione precedente, e considerare riuscita la prova in TEST
  solo se il dato e' arrivato davvero nel sistema di destinazione.

## Una traduzione vede un file solo

- **Una mappa puo' accorpare solo i dati che arrivano nello stesso file.** Ogni file e' una traduzione a se': se il
  partner manda un ordine per file (o una chiamata API per ordine), la mappa non vede gli altri e non puo' unirli. Se
  si chiede di accorpare (es. "stesso giorno e stesso indirizzo = una spedizione"), i dati devono arrivare nello
  stesso file, oppure l'accorpamento va fatto a monte o a valle della traduzione.

## Chiamate esterne e userexit

- **HTTPS da Java: chiedere `TLSv1.2` (o superiore) per nome.** Su IBM JDK 8 `SSLContext.getInstance("TLS")` puo'
  negoziare TLS 1.0, che i server rifiutano con `Received fatal alert: protocol_version`. In ogni userexit o classe
  che apre HTTPS scrivere `SSLContext.getInstance("TLSv1.2")`. Una prova da PowerShell/.NET non lo mostra: va provata
  dalla JVM di Sterling.
- **Chiamate REST con JSON costruito a stringa: escape dei valori, risposta letta per chiave, niente PUT ritagliate
  dalla GET.** Nelle extended rule il JSON si concatena (`^22` = `"`): ogni valore che viene dal file (ragioni sociali,
  indirizzi, note) va ripulito da `"` e `\` prima di inserirlo. Leggere la risposta cercando la chiave e il valore che
  segue, non con posizioni fisse (`strstr(...,"id")+5`, `mid(...,18,5)`): un campo nuovo o uno spazio in piu' nella
  risposta fa leggere valori sbagliati. Per un aggiornamento (PUT) costruire il JSON da zero dai dati del file, non
  ritagliando la risposta della GET.
- **Niente BP lanciati da una mappa.** La classe `BPLauncher` (`com.sterlingcommerce.woodstock.dmi.routing`) avvia un
  BP da una regola estesa, ma il BP chiamante non lo vede, non ne controlla l'esito e un errore non torna nel
  translation report. Il BP figlio si lancia dal BP, dopo la traduzione, leggendo dal ProcessData quello che la mappa
  vi ha scritto (`update ProcessData`).
- Le userexit non possono catturare ne' lanciare eccezioni: serve una classe wrapper (§ Best practice IBM).

## Nomi e regole estese

- **Regole estese: TAB al posto degli spazi e controllo SEMPRE dei caratteri totali.** Una regola estesa ha un limite
  di **65535 caratteri (64 KB)**: oltre, viene tagliata. Quando si crea o si modifica una regola:
  - indentazione con **un TAB per livello** e allineamenti (es. prima del `=`) con **un TAB**, mai con sequenze di
    spazi; dentro le stringhe (`"..."`) non si tocca niente; gli spazi singoli tra le parole possono restare (un TAB
    costa uguale). Script: `scripts\tabify_regole.py` (su mappe reali ha tolto circa il 10% dei caratteri);
  - **contare i caratteri** di ogni regola prima di consegnare: `controlla_mxl.py` da' errore oltre 65535 e avviso
    oltre il 90%, e stampa la regola piu' lunga. Dirlo all'utente. Ricontrollare anche dopo il salvataggio in `.map`
    (il Map Editor conserva i TAB). Le regole gia' vicine al limite (oltre l'85-90%) vanno prima compattate e poi
    estese.
- **Record senza ciclo (Max 1) dentro un gruppo: i campi si scrivono passando dal gruppo padre.** Esempio anonimo:
  `contact` e' un record Max 1 dentro il gruppo ripetuto `parties`. `$contact[iOrd][iParty].#phone` non compila
  (`ERRORE 2000 gruppo '$contact' non definito`, poi errori a cascata `syntax error 'end'` e `previsto 'END'`); si
  scrive `$parties[iOrd][iParty].#phone`, perche' il campo e' univoco nella mappa. Con un errore di questo tipo il
  Map Editor da' molti errori di sintassi dopo: correggere il primo e ricompilare.
- **Nomi degli oggetti nuovi** (mappe, XSLT): seguire il prefisso o lo schema di nomi del team, uguale a quello dei
  BP e dei servizi.
- **Nomi parlanti per variabili, contatori e campi temporanei.** Niente `n`, `i`, `z` o prefissi che sembrano un
  elenco puntato (`o_campo`): i contatori dicono cosa contano (`idxEvent`, `iOrder`, `totPackages`), le variabili cosa
  contengono (`sPartnerCode`, `dtEvent`, `hasMessageDate`), i temporanei (campi e gruppi) si chiamano **`TMP_` + il
  nome nell'output** (`TMP_OrderNumber`, `TMP_Item`), cosi' nelle regole si vede subito cosa e' temporaneo. Chi apre
  la mappa dopo deve capire la regola senza ricostruirla. Niente parole riservate come nomi (`riferimento-ibm.md` § 4).
- **Dopo ogni spostamento di tag, cambio di cicli o di tipo, ricontrollare tutte le regole.** Spostare un gruppo di
  livello, cambiare `Max` o `PromoteGroup` cambia il **ciclo a cui appartengono i campi**, quindi gli indici con cui
  le regole li raggiungono. Esempio: un gruppo temporaneo promosso con `Max` 1 non e' piu' un ciclo, e le righe
  `$TMP_gruppo[1][1].#...` non compilano ("is not a member of '<radice>'"): vanno scritte `$<radice>.#...`
  (`formato-mxl.md`, "Ciclo proprietario").
- **Non ricalcolare in mappa un valore che il BP mette gia' nel ProcessData**: leggerlo con
  `select xpathresult ... from processdata`.
- **`if`, `else` e `while`: il blocco va sempre tra `begin` ed `end`.** Senza `begin … end` la clausola vale solo per
  la prima istruzione che segue; le altre vengono eseguite sempre, anche quando la condizione e' falsa. Il Map Editor
  non da' errore. Forma da usare:

  ```
  if <condizione> then
  begin
  	...
  end
  else
  begin
  	...
  end

  idxDetail = 1;
  while idxDetail <= count($DETAIL[*]) do
  begin
  	...
  	idxDetail = idxDetail + 1;    // subito dopo begin oppure subito prima di end
  end
  ```

  Nei `while` l'indice si incrementa come **prima** istruzione dopo `begin` o come **ultima** prima di `end`, mai in
  mezzo al blocco: un incremento in mezzo viene saltato da un ramo `if`, e il ciclo non finisce piu' o rilegge la
  stessa riga. Se il ciclo esce con `break`, il `break` va dentro il proprio `begin … end`.
- **Commenti: `//` nelle regole estese della mappa, `/* */` nei JavaTask.** Nelle regole estese `/* ... */` non e'
  accettato: `ERROR 1007 syntax error '/'` sulla riga del commento e poi errori a cascata (`'parola' has not been
  defined`, `syntax error 'else'`, `'END' without 'BEGIN'`). Commenti su piu' righe: `//` all'inizio di ogni riga. Nei
  JavaTask inline invece un `//` commenta tutto il resto se il codice finisce su una riga sola: li' si usa `/* */`.
- **Numeri decimali (pesi, volumi, importi): `aton` e variabili `real`, mai `atoi`.**
  - `atoi` restituisce un intero e arrotonda ogni valore (820,7143 -> 821; 4,606 -> 5).
  - Un totale va accumulato in una variabile `real` dentro il ciclo, azzerata prima del ciclo di ogni documento, non
    solo dichiarata.
  - Il campo di output deve avere decimali (es. `R3`).
  - Errore tipico: assegnare all'output il valore dell'ultima riga invece del totale.
  - Dopo la modifica nella regola non devono restare le vecchie variabili intere.
  - Prima di copiare una mappa per un nuovo partner, controllare come calcola questi valori: i difetti si ereditano.
- **Fusi orari: `SimpleDateFormat.setTimeZone`, mai l'ora legale calcolata a mano.** Per convertire tra UTC e un fuso
  locale usare due `java.text.SimpleDateFormat` con `setTimeZone(...getTimeZone("Europe/Rome"))` (o il fuso che
  serve) e `parse`/`format`; il cambio di ora legale lo fa Java. Un calcolo a mano (cicli sui giorni di fine marzo e
  fine ottobre, `<< hours(1)`) sbaglia nelle ore del cambio.
- **`count()` su un gruppo vuoto restituisce -1, non 0.** `if count($G[*]) > 0` funziona, ma `if count($G[*]) = 0`
  per dire "gruppo assente" non scatta mai, e un contatore inizializzato con `count()` parte da -1. Controllare `<= 0`
  (o `< 1`). Fonte: IBM 6.2.0, topic `reference-count`.
- **Per togliere gli spazi si usa `trim(s)` senza secondo parametro, mai `trim(s, " ")`.** IBM indica come non valida
  la forma con `" "`; il secondo parametro serve solo per un carattere diverso dallo spazio. Fonte: IBM 6.2.0, topic
  `reference-trim`.

## Struttura del sorgente `.mxl` (temporanei e link)

- **Link e profondita' dei temporanei.** Con input XML il `<Link>` di un campo di output punta all'**ID del record
  `_pcd_`** dell'elemento di input, non al campo; lo specchio dei temporanei deve stare **alla stessa profondita'
  dell'output**, senza particle in mezzo. Con un livello in piu' o col link sul campo il Map Editor apre la mappa ma
  non mostra i temporanei come collegati. Gli `<ID>` devono solo essere univoci. Dettaglio: `formato-mxl.md`.
- **La regola sul lato input non scrive i campi di output: servono i temporanei linkati.** Una `OnEnd` dell'input che
  assegna `#CampoOutput` non compila (il campo non e' visibile dal lato input), e senza link l'output resta vuoto.
  Anche quando si rifa' l'output di una mappa da zero, rimettere in input i temporanei e un `<Link>` per ogni campo di
  output. Prima di modificare una mappa fuori dal Map Editor ripartire dallo schema della mappa stessa, non da
  supposizioni.
- **I temporanei vanno in una particle (o gruppo) con `Min` 0.** Non arrivano nel documento di input: con la particle
  obbligatoria il translator chiude con `Mandatory Block Missing` (codice 300) anche se l'output e' giusto.
  `controlla_mxl.py` lo segnala.
- **Ogni campo che una regola riempie deve uscire nel file tramite un link; se non serve, la riga si commenta.** Una
  regola che scrive un temporaneo (o un campo dell'input) senza che nessun campo di output sia collegato a quel campo
  non produce niente: il valore resta nella mappa e nel file non arriva, senza errori. Quando si aggiunge o si porta da
  un'altra versione una riga che scrive un campo, controllare anche il link in output. Se un'assegnazione e' voluta
  ma non deve uscire, si commenta la riga (`//`), cosi' chi legge capisce che e' intenzionale. `controlla_mxl.py` lo
  segnala ("scritto in una regola ma non collegato all'output").
- **Temporanei = specchio dell'output.** La logica sta di solito nella `OnEnd` della radice di input e riempie
  temporanei che ricopiano la struttura dell'output (gruppi e campi `TMP_` + nome nell'output), collegati all'output
  campo per campo, alla stessa profondita'. Non usare un gruppo piatto di temporanei: chi apre la mappa deve ritrovare
  l'output a sinistra.
- **Temporanei: tag che non combaciano con dati reali** (`$$$` nelle mappe EDI/posizionali, `XXX` nelle XML) e
  sempre condizionali (§ Best practice IBM).

## Lunghezza dei campi e tag dei record

- **Mappe che copiano la riga intera (prefisso + "Whole Record"): il campo deve coprire tutta la riga.** Se e' piu'
  corto della riga, il translator la taglia in silenzio e i campi oltre il taglio arrivano vuoti alla mappa
  successiva. Quando si clona una mappa di questo tipo, o si avvia un tracciato nuovo:
  - misurare la lunghezza delle righe nei file reali (in caratteri, non in byte se il file e' UTF-8) e usare quel
    valore per `Length`/`MaxLen`, **in input e in output**;
  - non fidarsi della lunghezza dichiarata dal tracciato (puo' essere diversa da quella dei file);
  - nella mappa che legge il file prefissato ricordare lo spostamento di `StartPos` dovuto al prefisso;
  - provare in TEST su un file reale e controllare che l'output non sia vuoto.
- **Cosa e' il TAG di un record, secondo la sintassi di input.** E' il valore con cui il translator riconosce a quale
  record appartiene un blocco di dati:
  - **posizionale**: il valore del tag viene cercato **all'inizio della riga** (a partire da `TagPos`); una riga che
    non comincia con il tag di nessun record non viene riconosciuta;
  - **EDIFACT**: e' il codice del segmento (`UNH`, `BGM`, `NAD`…);
  - **XML**: e' il nome dell'elemento.
- **Record senza tag: tag vuoto e `TagLength` 0, e controllarlo dopo ogni salvataggio nel Map Editor.** Un record di
  input posizionale con un tag (anche fatto di spazi) riconosce solo le righe che cominciano con quel tag. Le altre
  danno il warning `Code: 25 Unrecognized Data Block` (`Contains errors ? false`) e l'output e' vuoto: si perde tutto
  il file senza errore. Caso visto: sorgente con tag vuoto ma `TagLength` diverso da 0 (residuo della mappa copiata);
  risalvato nel Map Editor, il record si e' trovato con un tag di spazi (`BlockSig/Tag` nel `.mxl`) e ha scartato
  tutte le righe. Nel report il segnale e' `Unrecognized Data Block` su **ogni** riga.
- **Campi di testo libero e di riferimento: lunghezze ampie fin dall'inizio.** Note (FTX), nomi e indirizzi (NAD),
  email, descrizioni, riferimenti cliente e JSON con documenti allegati arrivano spesso piu' lunghi del previsto: la
  mappa va in `Data Exceeds Max Length` oppure tronca in silenzio. Dimensionare questi campi sul dato massimo
  realistico (per i JSON con documenti, sul documento piu' grande), non sull'esempio ricevuto. Limite di un campo:
  64 KB (§ Best practice IBM).
- **Campi numerici di input (volumi, pesi, quantita'): formato con decimali abbondanti.** Se il dato ha piu' decimali
  di quelli previsti dal formato del campo di input, la traduzione fallisce in INPUT con `Code: 110 Incorrect Data
  Format` e **tutto il file** resta fuori, anche se il campo non serve all'output. I partner mandano a volte valori
  calcolati (es. `38.30575`): dimensionare i decimali sul massimo realistico (almeno 5 per volumi e pesi); un campo
  intero va dichiarato con decimali se il partner puo' mandarne.

## Errori: dove guardare

- **Il dettaglio dell'errore di una mappa sta nello status report dello step Translation** (nel DB:
  `WORKFLOW_CONTEXT.STATUS_RPT` -> `TRANS_DATA`, gzip di una Hashtable Java; in console: il report dello step
  Translation del processo). Codici del report: `riferimento-ibm.md` § 12.
- **Prima di correggere la mappa, controllare l'input.** `Mandatory Block Missing` e gli errori di validazione del
  sistema a valle spesso dipendono da un dato che manca nel file del partner, non dalla mappa: in quel caso la
  richiesta va al partner. Esempi: un segmento obbligatorio dell'output che si costruisce da riferimenti che nel file
  non ci sono; un riferimento di collo mancante perche' nel file manca il segmento `MEA` che lo porta.
- **Correggere a mano il file sblocca quell'invio, non corregge i dati di origine.** Quando una mappa va in
  `Mandatory Data Missing` per un dato che manca a monte, un file corretto e ricaricato fa passare quell'invio, ma il
  prossimo con gli stessi dati fallisce allo stesso modo. Quindi: (1) chiedere sempre la correzione anche alla fonte;
  (2) annotare da dove vengono i valori inseriti; (3) un file ripassato con lo stesso nome non prova che il dato sia
  stato corretto: in mailbox `MBX_MESSAGE.USER_ID` distingue un caricamento automatico da uno fatto a mano.

## Versioni e passaggio TEST -> PROD

- **Prima di modificare una mappa, confrontare TEST e PROD: PROD vince sempre, ma se TEST ha evolutive in corso bisogna
  accorgersene e chiedere.** Si parte dal sorgente di PROD, la versione che gira davvero. Se in TEST c'e' una versione
  diversa (una modifica provata e non ancora rilasciata), **non si sceglie da soli**: si mostra all'utente cosa
  contiene (autore, data, commento, differenze) e si chiede quale portare avanti: solo PROD, oppure PROD piu'
  l'evolutiva di TEST. Altrimenti, salvando in TEST una versione costruita su PROD si cancella il lavoro di un collega.
  Come si controlla: in `MAP` (join `DATA_TABLE` su `UNCOMPILED_MAP`) confrontare versioni, autori, commenti e
  dimensione del sorgente (`DATALENGTH(DATA_OBJECT)`) in entrambi gli ambienti, e la versione predefinita in
  `MAP_VERSIONS`. Lo stesso vale per i BP e le configurazioni da cui la mappa dipende.
- **Qualunque caricamento da TEST a PROD porta lo stesso commento della versione di TEST da cui viene**, carattere per
  carattere (`MAP.COMMENTS`; lo stesso per XSLT, BP e altri oggetti versionati): confrontando i commenti si vede che
  le versioni sono identiche anche se i numeri di versione sono diversi. Il commento e' **corto** (una riga, una
  cinquantina di caratteri) e dice cosa cambia, non perche' (es. `Numero ordine da RFF+ON prima di RFF+CU`).
- **Quando si modifica una mappa, controllare e aggiornare anche il nome interno** (`Summary/Description`, che il
  translation report stampa come "Map Name" e "Translation Object Name" e che al check-in finisce in
  `MAP.DESCRIPTION`). Le mappe nate da copia si portano dietro il nome dell'originale, e nel report sembra di guardare
  un'altra mappa. `controlla_mxl.py` lo confronta con il nome del file.
- **Autore della mappa = chi la sta modificando.** Nel Map Editor, *Modifica > Dettagli*, campo **Autore** (nel `.mxl`
  `Summary/Author`): valorizzarlo secondo la convenzione del team; le mappe copiate si portano dietro l'autore
  dell'originale. `controlla_mxl.py --autore <VALORE>` lo controlla.
- **Una mappa caricata non e' attiva finche' non e' la versione predefinita** (`MAP_VERSIONS.DEFAULT_VERSION`):
  controllarla dopo ogni caricamento.
- **Prima del check-in controllare il nome del file, dopo controllare il nome in `MAP_VERSIONS`.** Il check-in prende
  il nome dal file: un file scaricato due volte, che Windows chiama `nome (2).txo`, crea in Sterling la mappa
  `nome (2)`. Risulta caricata e predefinita, ma il BP che la cerca col nome giusto non la trova e fallisce solo quando
  la usa; inoltre la console non riesce a cancellare una mappa con parentesi e spazio nel nome. Togliere ` (1)`,
  ` (2)`... prima del caricamento. Vale anche per BP e XSLT.
- **Su Sterling si carica il `.map` insieme al `.txo` compilato, non il `.mxl`.** Il `.map` occupa molto meno spazio
  nel DB; il `.mxl` serve per lavorare sul sorgente fuori dal Map Editor e si riconverte in `.map` prima del
  caricamento (`formato-mxl.md`).
- **Dopo il check-in controllare che `.map` e `.txo` siano della stessa mappa.** Sterling prende il `.map` (sorgente,
  `MAP.UNCOMPILED_MAP`) e il `.txo` (compilato, `MAP.COMPILED_MAP`) come due file separati e non controlla che vengano
  dalla stessa mappa. Con il `.map` sbagliato la versione gira bene (esegue il `.txo`), ma il sorgente salvato e' di
  un'altra mappa: chi lo esporta dopo lavora sulla mappa sbagliata, e se lo ricarica ne perde la logica. Dopo il
  check-in:
  1. `MAP.DESCRIPTION` della nuova versione deve essere il nome della mappa (nome interno);
  2. riesportare la versione appena caricata e guardare con `dump_mxl.py` che input e output siano quelli attesi;
  3. con dubbi sul compilato: il `.txo` e' gzip in `DATA_TABLE`; decompresso, le stringhe (segmenti, XPath, costanti)
     si confrontano con quelle della versione precedente.
  Chi trova una versione con il sorgente sbagliato parte dalla versione precedente buona e ci riporta le modifiche,
  ricavandole dal compilato, poi confronta le stringhe del proprio `.txo` con quelle del compilato in produzione.
- **Prova di non regressione prima del rilascio.** Una modifica chiesta per un caso (un codice, un formato, un
  instradamento) puo' colpire altri documenti che passano dalla stessa mappa. In TEST provare anche file fuori
  perimetro (altri sender, filiali, partner che usano la stessa mappa) e in PROD controllare per 48 ore i nuovi invii
  del partner.

## Best practice IBM (Map Editor)

Sintesi dei documenti IBM di best practice sul Map Editor; dove contrastano con una regola sopra, vale la regola sopra.

**Analisi e costruzione**
- Il tipo della mappa deve essere **Sterling B2B Integrator**. Caricando un DDF/IFD non si recuperano regole e link, e
  non si puo' fare Undo; aggiornando schema/DTD i link esistenti si perdono (ricontrollarli tutti).
- Validare schema XSD/DTD prima di caricarlo. Gli standard EDI devono essere installati sulla macchina del Map Editor;
  nel Map Editor caricare gli stessi formati data del server.
- Sequenza: analizzare input e output, correlare i campi, decidere link / standard rule / extended rule / temporanei,
  salvare spesso, compilare, testare.
- **Autolink prima dei link manuali**; View > Equalize per allineare i lati.
- **Link semplici solo tra componenti con stesso numero di occorrenze (loop), stesso livello, stesso tipo di dato**;
  almeno un link diretto verso ogni record di output (altrimenti il record non nasce). Non mappare se i livelli
  gerarchici non coincidono e mantenere la cardinalita' corretta.
- **Trigger: usare come campo che "accende" il record un campo di input obbligatorio.** Le regole su un record girano
  solo se almeno un campo del record ha dati.
- **Split** quando serve piu' di un'istanza di un componente ripetuto; Promote = split di una sola iterazione; **non
  usare Promote sul lato input**.
- **Mappe EDI inbound: attivare l'intera struttura EDI** (Activate Entire Side).
- **Temporanei** sempre **condizionali**; tag `$$$` nelle mappe EDI/posizionali e `XXX` nelle XML; nomi descrittivi.
- **Nomi dei campi univoci in tutta la mappa**; i tag sono case sensitive; un record con **tag vuoto combacia con
  qualunque record** dell'input.
- Con la Document Extraction su mappe di struttura simile, definire campi chiave in ognuna.
- Se il tag di un segmento finisce con spazi, salvare in formato `.map`.
- Mappe SQL: assegnare al record la Table/View giusta dal menu.
- Encoding di input impostato in base al file reale; syntax token dedicati per lingue dell'Europa occidentale /
  asiatiche (il null si mette nel token come `0x00`; `\` fa da rilascio per `^`, `"` e `\`).
- **Lunghezza massima di un campo 64 KB (65535)**: un valore maggiore viene troncato a 16 bit (la lunghezza diventa un
  numero diverso, senza errore).
- Se un Map Test va in timeout, controllare che i formati dei campi collegati siano compatibili.
- Il Map Editor non traduce file XLS. TRADACOMS: solo dati v9.
- Map Editor: client a 32 bit (MSXML 4.0); i date format personalizzati vanno aggiunti su ogni postazione.

**Standard rule ed extended rule**
- **Costanti con standard rule (Constant), non con extended rule.** Le standard rule sono mutuamente esclusive su un
  campo (System Variable, Constant, Loop Count, Accumulator, Code, Select, Update).
- System Variable solo su campi data/ora; Accumulator solo su campi numerici; una Select standard rule mappa al massimo
  8 campi.
- Extended rule: dichiarazioni prima, ognuna chiusa da `;` (`integer i; real r; datetime d; string[20] s;
  string[10] p[50];`), poi le istruzioni. Livelli: Pre-session, Post-session, On Begin / On End (eseguite **una volta
  per ogni occorrenza del ciclo**), regole di campo.
- **Niente parole riservate come nomi di variabile** (`REF`, `INTEGER`, `STRING`...).
- **Nei `while` incrementare sempre il contatore.**
- **Non passare campi/variabili real a integer.**
- **Controllare che il denominatore non sia zero prima di una divisione.**
- Le librerie di extended rule vanno nella cartella Extended Rule Library del Map Editor (e caricate su Sterling).

**Userexit (oggetti Java)**
- Le userexit chiamano classi Java (standard o di terze parti, installate con `install3rdParty`). **Non possono
  catturare ne' lanciare eccezioni**: serve una classe wrapper che chiama la classe vera e gestisce l'eccezione. Una
  userexit applicata a un componente puo' girare anche sui componenti figli.
- Esempi:

  ```
  object o; o = new("java.lang.String", #CAMPO); #CAMPO = o.toUpperCase();

  object dtNow, fmtTime; string[10] sTime;
  dtNow = new("java.util.Date");
  fmtTime = new("java.text.SimpleDateFormat", "HHmmss");
  sTime = fmtTime.format(dtNow);

  object fmtR2;                       // decimali fissi / zeri finali, output stringa
  fmtR2 = new("java.text.DecimalFormat", "0.00");
  #CAMPO_STRINGA = fmtR2.format(#CAMPO_REAL);
  ```

  `hhmmss` e' l'ora 01-12; per l'ora 00-23 serve `HH`. `DecimalFormat` funziona solo se il campo di destinazione e'
  stringa.

**Property del translator** (`customer_overrides.properties`)
- `translator.report.entryLimit` numero di voci del Translator Report.
- `OneBasedWeekNums` settimane dell'anno numerate da 1.
- `MaptestServiceEnabled` spegne il servizio di Map Test.
- `translator.input.allowsigneddecimal` / `translator.output.generatesigneddecimal` segno `+` in input / output per
  tutte le mappe; `translator.<mappa>.input|output...` per una mappa sola.
- `storage.keepTrailingZeros` / `storage.<mappa>.keepTrailingZeros` zeri finali sui numerici in output.
- `storage.useBigDecimal` BigDecimal invece di Double nei calcoli interni.

Prima di proporre una property, verificare il valore attuale sull'installazione: cambiarla in produzione e' una
modifica di configurazione (regola PROD dello `SKILL.md`).
