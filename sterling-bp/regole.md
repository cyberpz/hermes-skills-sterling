# Regole per i BP di Sterling B2B Integrator

Regole pratiche per scrivere e correggere BP (BPML) di IBM Sterling B2B Integrator. Nascono da casi reali e dalle
best practice IBM (in fondo). Una regola per punto: cosa fare e perche'. Se il vostro team ha regole proprie,
aggiungetele in fondo ("Regole del team"): dove contrastano, vincono quelle.

## Sommario
- Struttura e diagramma GPM: nomi univoci, onFault (un solo livello, codici, figli), impaginazione
- Choice, loop e assign: choice esclusive, loop sulla lista, multiassign, ciclo su piu' partner
- Parametri e valori fissi
- Documenti e ProcessData: DocToDOM, DOMToDoc, JavaTask, recupero dei documenti
- SQL nei BP: transazioni, deadlock, stored, colonne come contratto
- Retry e connessioni FTP/SFTP
- Lock
- Errori e notifiche
- Routing e mailbox
- Versioni e passaggio TEST -> PROD
- Nomi degli oggetti nuovi
- Best practice IBM (BPML e modellazione)

## Struttura e diagramma GPM

- **Nomi corti e univoci per sequence, choice, repeat e onFault.** Due attivita' con lo stesso nome confondono chi
  legge il diagramma e i `repeat` (che puntano per nome); IBM segnala che due sequence con lo stesso nome (es. i rami
  di una choice lasciati col nome di default del GPM) possono far finire un repeat o un ramo nella sequenza sbagliata.
  Anche un doppione gia' presente va rinominato quando si tocca il BP. Il contenuto di un onFault e' una `sequence`
  con un nome corto che dice cosa fa (`RETRY_CONN`, `END_KO_FILE`), non "onFault SS_CONNECT_TRY": il riquadro
  dell'onFault nel GPM prende quel nome (senza il prefisso `SS`).
- **Il contenuto di ogni onFault e' una sola `sequence`.** Cosi' sono tutti gli onFault salvati dal GPM.
- **Mai un onFault dentro il contenuto di un altro onFault: un solo livello.** Se un onFault contiene (a qualunque
  profondita') una sequence con un proprio onFault, quando scatta non esegue **nessuno** dei suoi step: il motore salta
  alla prima attivita' dell'onFault interno e l'istanza finisce, senza log, senza mail e senza il resto del gestore.
  Le sequence con onFault una dentro l'altra nel **flusso normale** vanno bene; il divieto riguarda solo il contenuto
  di un onFault. Cosa fare: l'onFault salva l'errore, imposta un flag (es. `/ProcessData/FILE_KO`) e toglie
  `ERROR_SERVICE` / `Prev_NotSuccess_Adv_Status`; il lavoro che puo' fallire (EndSession, invoke che possono andare in
  errore) va **dopo** la sequence protetta, in una `choice` sul flag, dentro una sequence con il suo onFault. Funziona
  perche' un onFault finito bene fa proseguire il processo con l'attivita' successiva alla sequence protetta.
  Un errore dentro un onFault (senza onFault annidati) non lo gestisce lo stesso onFault: risale a quello della
  sequence che lo contiene, e se fallisce anche quello l'istanza resta Halted. Tenere quindi gli onFault corti,
  soprattutto quello generale. `crea_bp.py` blocca gli onFault annidati.
- **Ogni BP ha un onFault che finisce bene: un processo Halted non viene mai purgato.** Solo i processi Completed e
  Terminated arrivano ad archivio e purge; Halted e Interrupted restano a DB. Un errore gestito da un onFault che non
  fallisce chiude il processo in Completed con la spia rossa. Lasciare un BP Halted apposta solo quando serve un
  intervento manuale.
- **onFault per codice d'errore: il default va per ultimo.** Un onFault con *Error Value* (`code`) scatta solo se il
  valore e' uguale all'Advanced Status del servizio (es. `No file to collect`) o all'`exceptionCode` del
  `BPExceptionService`. L'onFault senza codice prende tutto: se sta prima degli altri, quelli specifici non scattano
  mai.
- **Figlio senza onFault: scegliere `NOTIFY_PARENT_ON_ERROR` dell'invoke.** Con *Continue parent if any type error
  occurs* l'errore va all'onFault del padre; con *Halt sub-process* il figlio resta Halted senza gestione. Se il
  figlio ha il suo onFault, l'errore lo gestisce il figlio qualunque sia il parametro.
- **Impaginazione del diagramma.** Flusso da sinistra a destra. Una choice con piu' rami sta a meta' altezza tra il
  primo e l'ultimo ramo, e la sua choice end alla stessa altezza; una choice con **un ramo solo** resta sulla linea
  principale e il ramo va un livello sotto (risparmia spazio e si vede subito che e' un'opzione); le fine dei rami
  sono allineate in colonna. `crea_bp.py` genera il diagramma cosi'.
- **Dopo il salvataggio dal GPM riesportare e confrontare il BPML.** Il GPM rigenera il BPML dal diagramma: quello
  che il diagramma non porta (es. il `code` di un onFault) si perde in silenzio.

## Choice, loop e assign

- **Le regole di una stessa `choice` devono escludersi a vicenda.** Il motore le valuta dall'alto verso il basso e
  prende il **primo** `case` la cui regola e' vera: se due regole si sovrappongono si finisce nel ramo sbagliato senza
  nessun errore. Quando si aggiungono rami: (1) scrivere ogni regola in modo che sia falsa per i casi degli altri
  rami, non contare sull'ordine; (2) con piu' di due rami elencare a mano le combinazioni dei casi e controllare che
  per ognuna sia vera **una sola** regola; (3) i rami "tutto il resto" si scrivono come negazione esplicita
  (`negative="true"` sulla stessa regola) o come regola propria, non come ultimo `case` che cattura quello che avanza.
  Nessun case vero = si prosegue dopo la choice.
- **Piu' assign consecutivi si raggruppano in un solo `AssignService` (multiassign).** Un'operazione (participant
  `AssignService`, messaggio `AssignServiceTypeInputMessage`) con dentro tutte le `<assign>` nell'ordine voluto, dopo
  la prima `<assign to="." from="*">`, con un nome parlante (`Parametri Configurazione`, `Parametri Risposta`).
  Risparmia spazio nel diagramma e tiene i parametri in un punto solo. Le assign dentro lo stesso servizio vedono i
  valori scritti dalle precedenti (si possono usare anche percorsi relativi). Il servizio di solito **non e' tra
  quelli proposti dal GPM**: si porta copiando l'operazione da un altro BP o dal BPML. Eccezioni: `DocToDOM` e
  `DOMToDoc` (e le assign che li contengono) a volte non si riescono a elaborare nello stesso servizio: restano assign
  a se'. In generale si raggruppa tutto, si prova in TEST e si separano solo le righe che non funzionano. Non copiare
  in documentazione o note i valori sensibili (password, secret) che si trovano in questi servizi.
- **Loop: lista nel ProcessData, sempre l'elemento di posto 1, release prima del repeat.** (1) Gli elementi da trattare
  stanno in una lista nel ProcessData (es. `/ProcessData/LIST/Item`, copiata con un'assign); (2) la regola della
  `choice` che apre il giro controlla che ne esista almeno uno: `count(/ProcessData/LIST/Item) > 0`; (3) i servizi del
  giro lavorano sempre sull'elemento `[1]`; (4) **subito prima del `repeat`** un `ReleaseService` con `TARGET`
  `/ProcessData/LIST/Item[1]` toglie quell'elemento. Niente contatore `position() = N` per scegliere l'elemento.
  Perche': se un servizio si ferma, nel ProcessData l'elemento `[1]` e' proprio quello che si stava elaborando e ci
  sono ancora tutti i successivi. Se serve un numero d'ordine (es. per il nome del file) si usa un contatore a parte.
- **`repeat`**: `ref` = attivita' complessa che contiene il repeat; senza una condizione che cambia, ciclo infinito.
- **Ciclo su piu' partner (o elementi indipendenti): un elemento in errore non ferma gli altri, errore unico a fine
  giro.** La sequence del singolo elemento ha un onFault corto che **non** manda mail e **non** fa cose che possono
  fallire: aggiunge il nome dell'elemento a una lista nel ProcessData (es. `concat(string(/ProcessData/KO_LIST), <nome>,
  ' ')`) e il dettaglio a un secondo nodo (elemento, fase, servizio, primi ~150 caratteri di
  `ERROR_SERVICE/ADV_STATUS`), poi toglie `ERROR_SERVICE`, `Prev_NotSuccess_Adv_Status` e `message_to_child`; il ciclo
  prosegue. Finito il ciclo, una `choice` sulla lista: se non e' vuota, `BPExceptionService` con un `exceptionCode`
  leggibile (`<FLUSSO>_KO: <dettaglio>`, tagliato a qualche migliaio di caratteri) che porta all'onFault generale: una
  notifica sola con l'elenco. Se il BP ha un lock, l'eccezione va **prima** dello sblocco normale, cosi' lo sblocca
  l'onFault generale. Perche': con un errore generale il primo elemento con problemi blocca tutti i successivi; con una
  notifica per elemento un problema comune (servizio remoto giu') ne genera decine.

## Parametri e valori fissi

- **Niente valori fissi nel BPML dei BP condivisi tra piu' partner o ambienti.** Mittenti, destinatari, URL, codici,
  cartelle: se possono variare per partner vanno letti per partner (tabella di configurazione, property, parametri
  della schedulazione) con un default. Un valore cablato si cambia per tutti i partner insieme.
- **Pool JDBC, nomi di servizi e host che cambiano tra TEST e PROD** non vanno cablati se si puo' evitare; se sono
  cablati, la differenza va gestita al rilascio (vedi "Versioni").
- `sci-get-property` tiene in cache il file di property dalla prima lettura: dopo una modifica serve il Cache Refresh
  Service, altrimenti si legge il valore vecchio.

## Documenti e ProcessData

- **`DocToDOM(PrimaryDocument)` si scrive sempre `DocToDOM(PrimaryDocument,'false','false')`**, in ogni BP che si
  tocca: anche quelli gia' presenti vanno convertiti quando si prepara una nuova versione (nel BPML i parametri sono
  `&apos;false&apos;,&apos;false&apos;`). Senza il secondo `'false'` il parser tenta la validazione su un DTD
  inesistente e riempie i log di errori a ogni esecuzione. Assegnato al ProcessData (`assign to="." from="..."`) la
  radice resta come prima (`/ProcessData/<radice>/...`), quindi i percorsi a valle non cambiano; usato inline con un
  XPath accodato, il percorso parte dal secondo livello (senza il nodo radice).
- **Evitare `DocToDOM` sul documento intero; se serve, portare nel ProcessData solo i campi utili.** Non e' un
  divieto: va bene se il documento e' piccolo (pochi KB, tipo di messaggio che non cresce) o se non c'e' altro modo,
  ma non e' mai la prima scelta. Ogni `DocToDOM` analizza tutto il documento e costruisce l'albero in memoria;
  assegnato al ProcessData lo gonfia (e il ProcessData viene salvato a ogni step persistito). Ogni chiamata rifa' il
  lavoro da capo: una regola o un'assign con `DocToDOM` costa un'analisi completa ciascuna (su documenti di centinaia
  di MB, minuti). In ordine di preferenza: (1) ricavare i valori senza DOM (campi gia' nel ProcessData, nome file, un
  JavaTask che legge solo l'inizio del documento); (2) `DocToDOM` con il quarto parametro, che carica solo il nodo
  indicato; (3) un'unica analisi che scrive **solo i singoli campi** usati dopo, mai l'albero intero. Le regole delle
  `choice` leggono quei campi, non il documento.
- **Per leggere campi da un XML in un JavaTask usare StAX con il percorso, non le regex.** Un `XMLStreamReader`
  (`javax.xml.stream`, nel JDK di Sterling) legge un elemento alla volta senza costruire l'albero: si tiene il
  percorso degli elementi aperti e si prende il primo elemento il cui percorso finisce come l'XPath del BP, cosi' il
  risultato e' lo stesso di `(...)[1]/text()`. Si ferma appena ha tutti i campi, usa pochissima memoria e su un XML
  malformato va in errore come `DocToDOM`. Le regex non conoscono la struttura: prendono il primo testo che somiglia,
  anche in un ramo diverso.
- **Un JavaTask che cambia il comportamento di un BP si confronta su messaggi reali prima di andare in TEST.** Si
  scaricano in sola lettura i documenti che il BP ha prodotto (`WORKFLOW_CONTEXT` -> `DOCUMENT` -> `TRANS_DATA`, le
  pagine sono un unico gzip da concatenare), si esegue il codice del JavaTask in locale con la stessa versione di Java
  (classi finte per `Document` e `WorkFlowContext`) e si confronta con quello che il BP ha prodotto davvero. Il codice
  inline di un JavaTask ha un limite di 2048 caratteri: oltre, `srcLocationMode` = `File`.
- **`DOMToDoc` non e' un semplice taglio.** Il documento prodotto ha la dichiarazione `<?xml ... standalone="no"?>`,
  **perde il namespace**, attributi tra apici singoli, testi senza spazi in testa e in coda, un a capo dopo ogni tag
  di chiusura, elementi vuoti `<X/>`. Chi lo legge dopo (XSLT, mappe) si aspetta quel formato: un JavaTask che lo
  sostituisce deve riprodurlo e va confrontato con documenti reali. `assign to="." from="DOMToDoc(...)"` senza nome
  crea un documento chiamato `Document` (`/ProcessData/Document`), diverso dal `PrimaryDocument`.
- **Salvare il documento di uno step prima che il successivo lo sovrascriva**:
  `<assign to="doc1" from="PrimaryDocument/@SCIObjectID"/>` (nell'`input` dello step, o subito dopo).
- **Per sapere cosa e' finito in una mailbox guardare `MBX_MESSAGE.DOC_ID`, non il `DOC_ID` dello step
  `MailboxAdd`.** In `WORKFLOW_CONTEXT` il `DOC_ID` di uno step e' il documento primario del processo in quel momento;
  il `MailboxAdd` puo' aggiungere un altro documento.
- **Se un file inviato (per mail o altro canale) non arriva o non si legge, si recupera da Sterling, non si rilancia il
  flusso.** In `WORKFLOW_CONTEXT` si prende il `DOC_ID` del passo dopo quello che crea il documento, poi
  `DOCUMENT.BODY`, poi `TRANS_DATA.DATA_OBJECT` con le pagine in ordine di `PAGE_INDEX` concatenate in un unico gzip.
  Parametri dell'invio (oggetto, allegato, destinatari) sono nel ProcessData dello step di invio (anch'esso gzip in
  `TRANS_DATA`). Rilanciare il flusso manderebbe un secondo invio ai destinatari. Per confrontare il documento con
  quello ricevuto non contare gli a capo (CRLF/LF possono cambiare per strada).

## SQL nei BP

- **Controllare il livello di compatibilita' del database** a cui punta il pool prima di usare funzioni recenti
  (`STRING_AGG`, `OPENJSON`...). **Un commento `--` incollato nella query del BP la tronca in silenzio**: usare
  `/* */` o niente commenti. I pool del Lightweight JDBC Adapter possono avere nomi diversi tra TEST e PROD.
- **`BeginTransactionService` / `EndTransactionService` solo attorno a piu' query da confermare insieme.** Sospendono
  il commit automatico dei `LightweightJDBCAdapterQuery` fra di loro e lo fanno tutto all'`EndTransaction` (con
  rollback se uno step fallisce, secondo l'opzione On Fault): servono quando piu' query di fila devono riuscire o
  fallire insieme (es. testata + dettagli). Se racchiudono **una sola query** non servono e costano solo due step in
  piu': toglierle. **Verifica da fare ogni volta che si modifica un BP esistente**: dove c'e' una coppia Begin/End,
  contare le query che stanno davvero in mezzo, ramo per ramo; se in tutti i rami e' una sola, proporre di toglierla;
  se e' una sola solo in alcuni rami, dirlo all'utente con il peso dei rami (togliere la transazione solo li' di solito
  vuol dire duplicare lo step). Non usarle insieme all'opzione Enable Transaction del BP (fallisce).
- **Errore SQL 1205 (deadlock): prevedere la riprova automatica.** Un BP con `LightweightJDBCAdapterQuery` puo' essere
  scelto come vittima di deadlock; senza riprova ogni volta serve un riavvio manuale. Modello:
  - il `LightweightJDBCAdapterQuery` sta in una sequence propria con `onFault`, dentro una `choice` ripetuta con
    `<repeat ref="..."/>`; un contatore (`/ProcessData/QUERY_TRY`) e uno stato (`QUERY_STATUS` = `OK` / `KO` /
    `DEADLOCK`) decidono se ripetere;
  - nell'`onFault`: salvare `ERROR_SERVICE/ADV_STATUS` in un nodo proprio, riconoscere il deadlock con
    `contains(string(...),'1205') or contains(string(...),'deadlock')`, poi togliere `/ProcessData/ERROR_SERVICE` con
    `ReleaseService` (altrimenti un errore successivo si somma);
  - attesa breve con `TestSleepService` (`SLEEP_INTERVAL` in secondi, es. 30 s, massimo 3 tentativi); solo il deadlock
    si ripete, ogni altro errore SQL esce subito;
  - finiti i tentativi o su altro errore: `BPExceptionService` con `exceptionCode` leggibile
    (`QUERY_KO dopo N tentativi: <errore>`), che porta all'onFault generale.
  Provare in TEST anche il ramo della riprova, per esempio con una stored di prova che fa
  `RAISERROR('1205 deadlock test',16,1)`. Sui BP piu' colpiti analizzare anche le query concorrenti (indici, ordine di
  accesso alle tabelle).
- **XML passato a una stored come testo: togliere BOM e dichiarazione prima del CAST a xml.** Con `paramtype`
  `CharacterStreamFromDocument` Sterling manda il contenuto del documento come testo Unicode. Se il parametro della
  stored e' `nvarchar(max)` e il documento inizia con `<?xml ... encoding="UTF-8"?>`, il `CAST(... AS xml)` fallisce
  ("unable to switch the encoding"); un BOM davanti alla dichiarazione fa fallire anche un controllo come
  `LEFT(LTRIM(@x),5)='<?xml'`. Nella stored: `REPLACE(@x COLLATE Latin1_General_BIN2, NCHAR(65279), N'')` (con
  collation non binaria il carattere a larghezza zero puo' far tagliare il testo a `REPLACE`), poi togliere la
  dichiarazione se compare nei primi caratteri. Provare con: niente dichiarazione, dichiarazione UTF-8, BOM +
  dichiarazione, testo con accenti.
- **I nomi delle colonne di una stored o query chiamata dal JDBC adapter sono il contratto con chi legge a valle.**
  `LightweightJDBCAdapterQuery` scrive ogni colonna come elemento XML con il suo nome (dentro `row_name`), e la mappa
  che legge quel documento riconosce solo i nomi che conosce. Se si cambia la fonte di una stored o si rinomina una
  colonna, la mappa va in "Mandatory Block Missing" / "Unrecognized XML Element" e il file non parte, mentre la SELECT
  provata da sola sembra corretta. Prima di toccare una stored chiamata da un BP, cercare la mappa che ne legge
  l'output; tenere i nomi con alias o adeguare la mappa, e provare in TEST l'intera catena con dati reali.
- **Leggere l'esito di una stored di insert prima di scrivere le tabelle figlie.** Una stored che per scelta non
  scrive la riga (es. revisione piu' vecchia o uguale a quella presente) senza dare errore, seguita da insert figlie
  con chiave esterna sulla riga mancante, fa fallire il BP con un errore di vincolo (547) per un dato che in realta' e'
  gia' a posto. Succede tipicamente con due messaggi dello stesso oggetto elaborati in parallelo. Leggere il valore di
  ritorno e saltare le insert figlie (senza errore) quando la riga non e' stata scritta.

## Retry e connessioni FTP/SFTP

- **Riprovare solo gli errori di connessione, mai credenziali, host key e configurazione.** I testi vanno presi dagli
  errori veri del vostro sistema, non a memoria. Classificazione di partenza:
  - **da riprovare:** `Unknown host`, `Unable to locate server` (DNS), `Could not complete connection`,
    `closed by server`, `Closing connections`, `Connection refused` / `reset`, timeout, `Unable to access or verify
    mandatory service parameter`, `EOF received from remote side`, `Connection has been dropped as it reached max idle
    time`, `Idle connection`, `The channel unexpectedly terminated`, `Control connection has been closed unexpectedly`,
    `Conduit is closed`, `Failed to read binary packet data`, `temporary error condition` (FTP 4xx), `CONTROL_CLOSED`.
    Molti sono frequenti su CD e LIST: un retry che li ignora non riprova proprio i casi della LIST;
  - **mai:** `permanent error condition` (FTP 5xx, soprattutto 530), `Cannot authenticate`, `host key was not
    accepted`, errori di `key exchange` / negoziazione SSH, `No Such File` (CD su cartella inesistente, SFTP),
    `Permission denied`: riprovare non cambia niente, ritarda solo l'errore, e su credenziali sbagliate puo' bloccare
    l'utenza dal partner;
  - **ne' l'uno ne' l'altro** (errore subito): `Service Specific Exception (check status report)`, `General Failure`:
    il testo non dice la causa.
- **Schema.** Una sequence ciclo (es. `SS_CONNECT_LOOP`) che contiene: un'assign che azzera il flag `CONN_KO`; BEGIN
  SESSION + CD in una sequence con onFault; dopo, una `choice` sul flag. L'onFault fa solo cose che non falliscono:
  salva l'errore in un nodo proprio, imposta `CONN_KO`=Y, toglie `ERROR_SERVICE` e `Prev_NotSuccess_Adv_Status`. Il
  ramo della choice chiude la sessione se c'e' `TOKEN` (EndSession in una sequence con onFault propria), toglie `TOKEN`
  e `message_to_child`, invoca INLINE il BP (o la logica) di retry e fa `repeat` del ciclo. **Mai** EndSession
  protetta o `repeat` dentro l'onFault (un solo livello di onFault). Il BP di retry non lancia eccezioni: scrive una
  decisione (RETRY/STOP) e il motivo; l'eccezione (`BPExceptionService` con il motivo nell'`exceptionCode`) la fa il
  padre, nel ramo della choice. Riuscita la connessione, togliere i contatori del retry, altrimenti passano al file o
  al giro dopo.
- **Prima pausa con la Sleep, le altre con la Wait.** La `WaitService` libera il thread ma non torna in esecuzione
  prima di 30-40 s (sotto i 30 minuti la coda e' controllata ogni 30 s; oltre, la risveglia il `BPExpirator`, con un
  possibile ritardo di un ciclo); la Sleep tiene il thread ma rientra subito. Quindi primo tentativo dopo una Sleep
  breve (es. 10 s), i successivi dopo Wait crescenti.
- **BP di invio (delivery): attese che raddoppiano** (1, 2, 4, 8, 16, 32 min) fino a circa 1 ora in totale.
  **BP a polling (retrieval): retry breve** (es. 10 s, poi 1, 2, 3... min, fino a circa 20 minuti): lo scheduler
  rilancia comunque il BP ogni pochi minuti e durante le attese il lock del flusso blocca i giri successivi. Valori
  fissi e leggibili nel multiassign dei parametri, o passati dal chiamante.
- **Nel retrieval il retry copre anche la LIST**: dopo una LIST fallita si chiude la sessione, si riconnette, si rifa'
  la CD e la LIST dello stesso pattern; i contatori si azzerano solo dopo una LIST riuscita, altrimenti un server che
  accetta la connessione ma va sempre in timeout sulla LIST fa un ciclo infinito.
- **Sessione unica per tutti i file di un invio verso lo stesso server.** La sessione si apre quando manca `TOKEN`
  (primo file, o dopo un errore) e si chiude dopo l'ultimo file. Dopo un errore su un file, la sessione si chiude **e
  si toglie `/ProcessData/TOKEN`**: senza, il file successivo userebbe un token morto e fallirebbero tutti. Le
  EndSession nei rami d'errore stanno in una sequence con onFault propria (cosi' una connessione gia' caduta non fa
  fallire tutto il BP), ma **fuori** dall'onFault: l'onFault del file imposta un flag e la EndSession sta in una choice
  dopo la sequence del file. Quando i tentativi finiscono, uscire dal ciclo dei file (un flag nella regola del ciclo):
  i file rimasti restano nella mailbox.
- Parametri dell'adapter da conoscere: `ConnectionRetries` / `RetryDelay` della Begin Session SFTP (solo errori
  TCP/IP; `ResponseTimeout` deve superare il totale), `TranscriptDocumentId` dell'FTP client (dialogo col server, la
  prima cosa da guardare). Dettagli in `riferimento-ibm.md`.

## Lock

- **Lock Service se un BP o una risorsa non deve mai girare in piu' istanze**: due step (lock e unlock) con stessi
  `LOCK_KEY` e `USER`.
- **La durata del lock deve coprire le attese del BP.** IBM indica 2-3 volte il tempo di esecuzione stimato. Se il BP
  puo' aspettare a lungo (es. retry fino a ~1 ora con lock da 1 ora), il lock scade con il BP ancora in corso e il giro
  successivo dello scheduler parte sulla stessa risorsa. Quando si aggiungono attese a un BP con `LockService`,
  rivedere `DURATION` (in ms).
- **Il lock va rilasciato anche in errore**: l'onFault generale fa l'unlock. Un BP Halted tiene il lock finche' non
  scade o non lo si toglie a mano.

## Errori e notifiche

- **Non scrivere a mano `ERROR_SERVICE/SERVICE_NAME`; il motivo di un errore voluto va nell'`exceptionCode`.** Quando
  un servizio fallisce Sterling scrive da solo `/ProcessData/ERROR_SERVICE/SERVICE_NAME` e `ERROR_SERVICE/ADV_STATUS`
  (per `BPExceptionService` e' l'`exceptionCode`). Un `SERVICE_NAME` assegnato prima si somma al suo e l'avviso mostra
  i due testi attaccati. Il motivo leggibile va nell'`exceptionCode` (es. `NO_ROWS: la stored non ha restituito
  righe`).
- **Togliere `ERROR_SERVICE` (e `Prev_NotSuccess_Adv_Status`) con `ReleaseService` dopo aver gestito un errore** e
  prima di riprovare: altrimenti un errore successivo si somma al precedente.
- **Togliere `message_to_child` prima di lanciare un secondo figlio.** Se nel ProcessData c'e'
  `/ProcessData/message_to_child` (preparato per un primo invoke, es. il BP di notifica errori),
  `InvokeBusinessProcessService` passa al figlio **solo quel nodo**, non il ProcessData: un secondo invoke riceve i dati
  del primo e non i propri parametri ne' i documenti ("Primary Document not Present"). Prima del secondo invoke:
  `ReleaseService` con `TARGET` `/ProcessData/message_to_child`.
- **Lo step `InvokeBusinessProcessService` con `BASIC_STATUS` 3 non e' un errore: l'esito vero e' quello del BP
  chiamato.** Lo step che lancia un figlio puo' restare con stato 3 anche quando il figlio finisce bene. Per sapere se
  un invio e' andato si guarda il processo figlio: i suoi step devono avere `BASIC_STATUS` 0 fino al servizio finale.
- **Se il BP legge i destinatari delle notifiche da una tabella di configurazione, verificare che esista la riga
  (o il default) per il nuovo partner/flusso.** Senza, l'SMTP fallisce con `Destination address not specified` e
  proprio l'avviso d'errore non parte.
- **Copiando un BP modello, allineare la regola del ramo d'errore a dove la mappa (o il servizio) scrive l'esito.** Se
  la regola legge `/ProcessData/BPERROR` ma la mappa scrive l'esito in un altro nodo, il ramo d'errore non scatta mai e
  gli errori si vedono solo dai log. Verificare con un caso di errore in TEST che il ramo parta.
- **Nei BP che chiamano un web service, l'onFault esterno non deve coprire il motivo, e la risposta va controllata e
  conservata.** Se ogni sezione ha il suo `exceptionCode` ma l'onFault generale rilancia sempre un codice generico,
  chi monitora vede solo quello. Portare nell'`exceptionCode` finale il codice della sezione; controllare lo stato
  applicativo della risposta (non solo l'HTTP 500: lo stato del client HTTP e' il codice HTTP, non 0/1); conservare
  la risposta (file o log). "Invocato con successo" non prova che il destinatario abbia accettato il documento.

## Routing e mailbox

- **Regex di routing: punto escapato e fine ancorata con `$`.** Una regex come `^[0-9]+.206` cattura anche file il cui
  timestamp contiene `206`, e il BP a valle fallisce su file che non sono suoi. Quando si scrive o si cambia una regex,
  confrontarla con quelle degli altri flussi sulla stessa cartella.
- **Upload con nome temporaneo: restringere il pattern della regola mailbox.** Se il partner carica con un nome
  temporaneo e poi rinomina (`.inprocess`, `.tmp`), una regola con pattern `%` puo' lanciare il routing sul temporaneo,
  che quando il BP lo estrae non c'e' piu' (`Mailbox Message Not Found`). Il pattern va limitato al nome finale (es.
  `%.xml`).
- **Ogni messaggio e' valutato dalle regole di routing automatico una volta sola**: se all'arrivo nessuna regola lo
  prende, non verra' ripreso nemmeno da una regola creata dopo (serve un resubmit con il Mailbox Update Service).
- **File di prova caricati in PROD: `TEST_` in chiaro davanti al nome originale**, cosi' chi guarda log e processi
  capisce che non e' arrivato dal partner. Prima provare il nome contro **tutte** le regex della mailbox di arrivo e
  di quelle dove finisce dopo: un prefisso passa solo se le regex non sono ancorate con `^`. Se il nome con prefisso
  non e' mai passato dal flusso, fare prima un giro in TEST.
- **Deenvelope EDIFACT in ingresso: `BatchLikeTransactions = NO` se il partner puo' mandare piu' messaggi nello stesso
  file e il passo dopo si aspetta un messaggio per documento.** Con `YES` tutte le transazioni finiscono in un solo
  documento, la traduzione scrive piu' XML uno dopo l'altro e il passo successivo puo' fallire ("markup following the
  root element must be well-formed") mentre la traduzione risulta riuscita. Provare in TEST con un file con almeno due
  messaggi.

## Versioni e passaggio TEST -> PROD

- **Ogni BP nuovo o nuova versione si carica con un commento corto**: una riga, al massimo una cinquantina di
  caratteri, cosa cambia e non perche' (es. `retry su BEGIN, CD e LIST`). E' `WFD.DESCRIPTION`, l'unica cosa visibile
  nell'elenco delle versioni senza aprire il sorgente.
- **Da TEST a PROD lo stesso commento, carattere per carattere.** I numeri di versione non coincidono tra gli ambienti:
  solo i commenti uguali dicono che le versioni sono identiche. Dopo il caricamento confrontare contenuto **e**
  commento. Vale per tutto cio' che si carica con un commento (BP, mappe, XSLT, buste...).
- **Servizi con nomi diversi tra TEST e PROD** (es. servizi generati da WSDL): lo stesso BPML non gira in tutti e due;
  si prepara una bozza per ambiente, uguali salvo `participant` e `message` di quei servizi. Il corrispondente si trova
  partendo dalla versione predefinita dell'altro ambiente (il servizio che usa per la stessa operazione), non per
  somiglianza di nome. Dopo la sostituzione, il diff tra le due bozze deve mostrare solo quelle righe.
- **Un BP salvato non e' attivo finche' non e' la versione predefinita** (`WFD_VERSIONS.DEFAULT_VERSION`; per le mappe
  `MAP_VERSIONS.DEFAULT_VERSION`). Dopo un rilascio verificare quale versione e' predefinita.
- **La versione predefinita nuova non sempre parte subito.** Le esecuzioni lanciate per nome possono continuare a usare
  la versione precedente per qualche decina di minuti. Controllare la versione delle esecuzioni nuove
  (`WF_INST_S.WFD_VERSION`, o `WORKFLOW_CONTEXT.WFD_VERSION`) finche' non compare la nuova. `WF_INST_S` puo'
  aggiornarsi in ritardo: per gli ultimi minuti contare da `WORKFLOW_CONTEXT`, altrimenti sembra che il BP si sia
  fermato.
- **Dopo un rilascio verificare il risultato, non l'assenza di errori**: stesso ritmo, stessi passi per flusso della
  versione precedente, oggetti prodotti che esistono davvero (mailbox, consegne, BP successivi).
- **Prova di non regressione prima del rilascio di un BP condiviso.** Una modifica chiesta per un partner o un flusso
  puo' rompere l'output di altri flussi che usano lo stesso BP. In TEST provare anche i flussi fuori perimetro e in PROD
  controllare gli invii nei giorni successivi.
- **Dismettendo un flusso, cercare anche le schedulazioni** (`SCHEDULE`) che lanciano i suoi BP: disabilitare il
  flusso da un altro strumento non ferma gli scheduler di Sterling.

## Nomi degli oggetti nuovi

- **Un prefisso unico per tutto quello che si crea su misura** (BP, servizi, JavaTask, adapter, mappe, XSLT,
  schedulazioni), es. `<CLIENTE>_*`: cosi' si distinguono subito dagli oggetti IBM e dai vecchi nomi senza prefisso.
- **Rinominando uno step nel GPM, tenere il nome del servizio nel nome** (es. `Assign - parametri`, `FSA Extract`): il
  rename cambia solo l'etichetta; quando un servizio va sostituito si trovano subito i BP che lo usano.

## Best practice IBM (BPML e modellazione)

Sintesi dei documenti IBM *BPML Best Practices* e *Business Process Modeling Best Practices* (2013-2014). Dove
contrastano con le regole sopra, vincono quelle sopra.

**Struttura**
- Bootstrap adapter (File System, SFTP, Mailbox...) fuori dal BP: non mettere l'adapter che fa partire il processo
  come primo step, cosi' la configurazione si riusa per altri BP.
- Sottoprocessi piccoli e riusabili; usare i BP predefiniti di Sterling quando esistono.
- Modifiche incrementali, provando ogni passo prima del successivo.
- Servizi e adapter correnti, non quelli in retiring (stencil "Retiring" nel GPM): es. FTP Client suite invece di FTP
  Send Adapter. Meno step e meno accessi al DB.

**Messaggi verso il servizio (Message To Service).** L'opzione "Output Msg" decide chi vince tra ProcessData e assign
dello step:
- *Obtain Process Data first, then Messages* (default): passa tutto il ProcessData, poi gli assign dello step lo
  sovrascrivono. Scelta normale.
- *Obtain Message first, then Process Data*: gli assign sono sovrascritti da quello che c'e' nel ProcessData. Causa
  tipica di "il BP va in loop" o di un parametro che non prende il valore scritto nello step.
- *Messages Only*: passa solo gli assign espliciti; mancano anche `PrimaryDocument` e simili.
Diagnosi: se un servizio non usa il valore assegnato nello step, controllare prima questa opzione, poi i nodi lasciati
nel ProcessData da servizi precedenti (es. un `b2b-raw-message=true` rimasto da un servizio mail che cambia il
comportamento dell'SMTP Send): Release del nodo prima del servizio.
- *Input Message (Message From Service)*: *Allow Process Data write* mette il risultato nel ProcessData; *Allow
  message write* lo lascia nel messaggio e nel ProcessData arriva solo quello che si assegna dentro `<input>`.
- Il "Message To Service" si vede nel monitor solo se almeno un parametro dello step e' un XPath.

**Invoke, cicli e documenti**
- Invoke inline quando possibile (stesso processo, niente costo di un processo nuovo). In sviluppo puo' convenire sync
  (il figlio si vede a se' nel monitor). Async solo per "fire and forget": il padre non vede le modifiche del figlio.
- Passare i dati ai figli con `message_to_child` / `message_to_parent`.
- **`For Each Document` + `Invoke Business Process` in ciclo: rischio "production down".** Ogni figlio si porta dietro
  tutti i documenti e il ProcessData del padre: N cicli = N copie, il DB si riempie. Due modi corretti: (1)
  `assign to="message_to_child" from="PrimaryDocument"` prima dell'invoke **e** `ReleaseService` con `TARGET`
  `message_to_child` **dopo** l'invoke (mai tra assign e invoke); (2) assign a `message_to_child` dentro il Message To
  Service dell'invoke (il Release non serve). La validazione al check-in segnala il ciclo sbagliato.
- `All` (rami in parallelo) solo se i rami durano secondi o minuti; non per lanciare piu' istanze dello stesso
  sottoprocesso.
- Pochi step: niente letture DB ridondanti per dati gia' nel ProcessData.

**Prestazioni e carico**
- XPath con percorso esplicito (`/ProcessData/...`), mai `//`: visita ogni nodo del ProcessData, e in un ciclo
  rallenta in proporzione alla sua dimensione.
- Persistenza minima necessaria: Full solo se serve (o in test); persistere gli step che generano dati non ripetibili
  (es. control number dell'envelope), non le letture di dati statici.
- Sleep tiene il thread, Wait no: per attese oltre ~1 minuto Wait; Sleep per attese brevi o quando serve precisione.
  Molti BP "addormentati" insieme esauriscono i thread.
- Get Document Info, BP Metadata Info e simili solo nell'`onFault` se servono solo in caso di errore.
- Schedulare i BP pesanti fuori dalle ore di punta, con la frequenza necessaria; preferire elaborazioni batch.
- Prima farlo funzionare, poi (provato) renderlo piu' veloce.

**Funzioni estese negli `assign`**

| Funzione | Cosa fa |
|---|---|
| `sci-get-property('file','chiave')` | legge una chiave da `<install>/properties/file.properties` (in cache: vedi Cache Refresh) |
| `sci-set-property('chiave','valore')` | property globale **in memoria** (persa al riavvio); si assegna a `to="sciGlobalProcess"` e si rilegge con `sci-get-property('sciGlobalProcess','chiave')` |
| `Status_Rpt('Nodo')` | copia lo status report del servizio appena eseguito nel ProcessData (nell'`<input>` dell'operation) |
| `getUniqueID()` | ID univoco, piu' veloce del vecchio servizio This; utile come chiave di insert |
| `DocToDOM(PrimaryDocument,'false','false')` | analizza un documento XML nel ProcessData; si puo' accodare un XPath senza il nodo radice |
| `DOMToDoc(xpath,'NomeDoc','no','root')` | applica un XPath al ProcessData, avvolge il risultato nella radice indicata e lo crea come documento |

## Regole del team

(Aggiungere qui le regole proprie del vostro team o cliente: una per punto, cosa fare e perche'.)
