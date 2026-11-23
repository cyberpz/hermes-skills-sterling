# Riferimento IBM per i BP (Sterling B2B Integrator 6.2.0)

Servizi, adapter e attivita' BPML piu' usati nei BP, riassunti dalla documentazione IBM 6.2.0. Da aprire solo quando,
lavorando su un BP, si incontra un servizio, un parametro o un errore che non si conosce.
- **Uso:** cerca la voce (nome o system name, es. `ExecutionControlService`) e leggi solo quella sezione. Per i
  dettagli non coperti apri nel browser la pagina IBM: `https://www.ibm.com/docs/en/b2b-integrator/6.2.0?topic=`
  seguito dal topic scritto tra apici inversi nella voce (es. `l-lock-service`).
- Valgono prima le regole di `regole.md` (Message To Service, inline/async, ForEachDocument + Invoke, XPath,
  persistenza, Sleep/Wait, `sci-get-property`, `DocToDOM`/`DOMToDoc`, `Status_Rpt`): qui non si ripetono.
  "(non specificato dalla pagina)" = IBM non lo dice.

## Sommario
- Controllo del BP: Lock, Release, For Each Document, Java Task, Execution Control, This, Begin/End Transaction, BP Metadata, Timestamp Utility, Invoke Sub-Process, Wait, Sleep, BP Exception
- Documenti: Get Document Info, Document Keyword Replace, MergeDocument, XSLT, Text Appender, XML Encoder, Mail Mime/MIME, XML JSON, Encoding Conversion
- Mailbox e routing: Add, Extract Begin/Commit, Query, Update, Correlate, Evaluate All Automatic Routing Rules
- FTP e SFTP client · HTTP, SOAP e REST · File system · Database (Lightweight JDBC) · Email
- Sistema e manutenzione: Cache Refresh, XAPI, CLA2, servizi di sistema
- EDI e altri servizi · Concetti utili dei servizi · BPML · Monitoraggio e troubleshooting · Pagine IBM chiave · Non trattati qui

## Controllo del BP

### Lock Service
`LockService` · `l-lock-service`
- Coppia lock/unlock e `DURATION`: vedi regole.md § Lock.
- `ACTION`: `Lock` (default), `Unlock`, `Touch` (rinnova), `Check` (scrive `LOCK_EXIST` true/false), `List Locks`. `LOCK_KEY` e `USER` uguali nei due step; `DURATION` in ms.
- Solo BPML: `CLEAR_ON_START_UP` (lock tolto al riavvio), `IN_TRANSACTION` (default false).
- BP in Halted: il lock resta finché non scade o non lo si toglie a mano.

### Release Service
`ReleaseService` · `z-release-service`
- Toglie nodi dal ProcessData. `TARGET` **tutto maiuscolo**; costante `<assign to="TARGET">nodo</assign>`, XPath `from="'xpath'"` con "Use XPATH?".
- Su `PrimaryDocument` toglie solo il riferimento. Consiglio IBM: nodi temporanei sotto un padre unico, un solo Release.

### For Each Document Service
`ForEachDocument` · `l-each-document-service`
- A ogni giro rende `PrimaryDocument` il documento successivo (tipico dopo Document Extraction).
- `ITERATOR_NAME` = prefisso dell'output: `I.INDEX`, `I.NAME`, `I.DONE` (0 = altri documenti, 1 = finito). Filtri `DOCUMENT_NAME_PREFIX` o `DOCUMENT_KEY_PREFIX` (vince KEY); senza, tutti i documenti del BP.
- Ciclo: `choice` su `I.DONE = 0` e `repeat` sulla sequence che contiene il ForEach. Invoke nel ciclo: vedi regole.md § Best practice IBM.

### Java Task Service
`JavaTask` · `l-java-task-service`
- Codice Java con `wfc` (WorkFlowContext) e `log`, restituisce una stringa. `srcLocationMode` `Inline` (`javaSrc`, **massimo 2048 caratteri**) o `File` (`javaFile`). Regole (StAX, confronto su messaggi reali): regole.md § Documenti.

### Execution Control Service
`ExecutionControlService` · `l-execution-control-service`
- Cambia a runtime coda, priorità, step per ciclo e deadline del BP (prestazioni). Persistenza None.
- `queueName` 1-9: sposta il BP di coda (più bassa = libera thread per i prioritari). `priority` 1-9 (default 4) dentro la coda.
- `executionCycleSize` (default 10): step eseguiti prima di rimettersi in coda; alto = tiene il thread, basso = lo cede spesso.
- `yield` (default false): cede il thread. **Le altre modifiche valgono subito solo con `yield` = true.**
- `deadline` in ms (formato di Timestamp Utility). Cluster: `preferredNode`, `mandatoryNode` (errore se il nodo manca).

### This Service
`This` · `z-this-service`
- **In via di ritiro**: IBM indica BP Metadata Info, Get Document Info, Release, Timestamp Utility, `getUniqueID()`.
- La funzione la decide il nome del messaggio di output: `thisRequest`, `giveDocumentRequest`, `takeDocumentRequest`, `getDocumentName`, `releaseRequest`, `assignRequest`, `timeRequest`, `timeDiffRequest`. Output `documentId`, `documentName`, `time`, `elapsedTimeMillis`.

### Begin / End Transaction Service
Begin `l-begin-transaction-service` · End `l-end-transaction-service`
- Gli step tra Begin ed End sono una transazione unica. Begin: `START_TRANSACTION` true; `DISTRIBUTED` true per gli adapter transazionali (es. Lightweight JDBC); On Fault Rollback/Commit, **default Commit** (nome BPML: non specificato dalla pagina).
- End: `END_TRANSACTION` true; `Rollback_Transaction` true annulla per scelta del BP. Pool JDBC con `<pool>.transactional=true`.
- Non insieme a Enable Transaction del BP (§ BPML).

### BP Metadata Info Service
`BPMetaDataServiceType` · `l-bp-metadata-info-service`
- Scrive `WFD_ID`, `WFD_NAME`, `WFD_VERSION`, persistenza, stato del BP corrente o di `WORKFLOW_ID`; opzioni `LINKAGE`, `DISPOSITION`, `TRACE`, `CORRELATION`.

### Timestamp Utility Service
`TimestampUtilService` · `z-timestamp-utility-service`
- `action` Current Time / Add / Subtract / Format; `baseTime` (anche `now`; ms se manca `scale`), `baseTimeFormat` (se manca, `baseTime` può essere ctime UNIX), `format` SimpleDateFormat, `offsetTime`, `scale` Day/Hour/Minute/Second/Millisecond.
- Risultato preso nell'`<input>` (esempio IBM `to="/ProcessData/calculated" from="*"`); nome del nodo: non specificato dalla pagina. La pagina dice sia che senza `assign to="." from="*"` il risultato può essere errato, sia che con quel jolly può dare errore: provare in TEST. Non converte da data a timestamp UNIX.

### Invoke Sub-Process Service
`InvokeSubProcessService` · `l-invoke-sub-process-service`
- `WFD_NAME`; `INVOKE_MODE` async (default) / sync / inline / embedded; sync non va con persistenza Error Only. `PASS_STATUS_REPORT` (default ON_ERROR), `PARM_LIST` (`n1=v1&n2=v2`). `NOTIFY_PARENT_ON_ERROR`: regole.md § Struttura.
- Figlio con persistenza non Full: forzare la persistenza del suo ultimo step, altrimenti il padre non trova il ritorno. Il padre resta fermo se il figlio è disabilitato o fermato; si sblocca con il resume del figlio.

### Wait / Sleep / BP Exception
- Wait `WaitService` `z-wait-service`: `WAIT_INTERVAL` + `units`; sotto i 30 min coda "0" controllata ogni 30 s, oltre lo risveglia `BPExpirator` (default ogni 15 min, l'attesa può allungarsi di un ciclo).
- Sleep `TestSleepServiceType` `z-sleep-service`: `SLEEP_INTERVAL` (s) o `MSEC_SLEEP_INTERVAL`. Scelta tra i due: regole.md § Retry.
- BP Exception `BPExceptionService` `l-bp-exception-service`: errore con `exceptionCode` come Advanced Status (default `si:general`), che l'onFault con codice confronta.

## Documenti e trasformazioni

### Get Document Info Service
`GetDocumentInfoServiceType` · `l-get-document-info-service`
- Metadati del primario senza aprirlo: `DocumentName`, `DocumentId`, `DocumentBodyLength`, `DocumentContentType`, `DocumentCharEncoding`, `DocumentFileName`, `DocumentStorageType`...
- `DocumentId` di un altro documento: **lo carica come PrimaryDocument, sovrascrivendo l'attuale**.
- Per cambiarli si passano `DocumentContentType`, `DocumentCharEncoding`, `BodyName`; `doClone=true` lavora su una copia. `CORRELATION` (default false), `RETRIEVE_INITIAL_DOC_ID` (default true).

### Document Keyword Replace Service
`DocKeywordReplace` · `l-document-keyword-replace-service`
- Coppie `keyword1`/`replace1`... **senza buchi**: dal primo buco le coppie seguenti sono ignorate.
- `literal_mode=true`: la più veloce, consigliata; buffer `literal_bufferSize` (10240) > `literal_readAheadSize` (8192); può cancellare caratteri.
- `mode=String` (default): keyword tra `keystart` `${` e `keyend` `}` salvo `useKeywordDefaults=false`; non sostituisce `ABC` con `ABCD` (anti-loop). `mode=Document`: inserisce un documento. Caratteri speciali in `keystart`/`keyend` solo da BPML.

### MergeDocument Service
`MergeDocument` · `z-mergedocument-service`
- Concatena due documenti nel PrimaryDocument, **senza separatori**.
- `document1`/`document2` = **nome del nodo** come stringa (`from="'doc1'"`). Salvare ogni documento subito dopo lo step che lo crea (`assign to="doc1" from="PrimaryDocument/@SCIObjectID"`), prima che il successivo sovrascriva il primario.

### XSLT, Appender, XML Encoder, Encoding Conversion
- XSLT `XSLTServiceType` `z-xslt-service`: `xslt_name`, `xml_input_from` (primary document / process data + `input_pd_xpath`), `xml_input_validation`, `additional_xslt_params`; errore nello status report.
- Text Document Appender `DocAppend` `z-text-document-appender-service`: `appendString` in fondo al primario (lo crea se manca).
- XML Encoder `XMLEncoderType` `z-xml-encoder-service`: `map_name`, `mode` (Encode non-XML / Use existing XML / Create document using XPATH), `output_to_process_data`; l'encoding del documento prevale su quello della mappa.
- Encoding Conversion `EncodingConversionType` `l-encoding-conversion-service`: `input_encoding` → `output_encoding`.

### Mail Mime / MIME Service
`MailMimeService` `z-mail-mime-service` · `MIMEServiceType` `z-mime-service`
- Mail Mime: `mail-mime-operation` build/parse; corpo = primario, `mail-mime-sender`/`-recipient`/`-subject`; allegati da file (`mail-mime-attachment-count` + `mail-mime-attachment<n>`, percorso completo) o `mail-mime-use-doc-area=true`; in parse allegati in `Mail_Mime_DOC_<n>`. Niente streaming oltre 900 MB.
- MIME: `packRequest`/`crackRequest` come nome del messaggio; in codifica serve la struttura `mime:message` nel ProcessData (se è sbagliata il servizio fallisce) e `mime-document` va assegnato a mano al PrimaryDocument.

### XML JSON Transformer service
`xmljsontransformer` · `z-xml-json-transformer-service`
- `Input`, `InputType`, `OutputPath` con maiuscole esatte. XML→JSON perde l'ordine; JSON→XML aggiunge `<root>`, perde gli array vuoti, niente dichiarazione; JSON massimo 50 MB.

## Mailbox e routing

Permessi verificati a runtime sull'utente del BP. Regex e pattern: regole.md § Routing e mailbox.

### Mailbox Add Service
`MailboxAddServiceType` · `z-mailbox-add-service`
- `MailboxPath` (inizia con `/`), `MessageName` (default nome del documento, vietati `? < > | / \ " %`, massimo 255).
- **Una sola** tra `Extractable`, `ExtractableCount`, `ExtractableUntil`, altrimenti "Multiple Extractable Types". Se ci sono primario e `DocumentId` vince `DocumentId` (in un ciclo toglierlo dopo ogni add). Output `MessageId`.

### Mailbox Extract Begin / Commit Service
Begin `MailboxExtractBeginServiceType` `z-mailbox-extract-begin-service` · Commit `z-mailbox-extract-commit-service`
- `CommitNow` No (default): messaggio bloccato fino a Commit/Abort; Yes: conferma subito (in errore il contatore non torna). `ViewOnly=Yes` sola lettura.
- Commit: **stessa istanza e stesso ramo** della Begin.

### Mailbox Query Service
`MailboxQueryServiceType` · `z-mailbox-query-service`
- Elenco nel ProcessData (`MessageId`, `DocumentId`, `MessageName`, `MessageSize`, `CreateDateTime`, `CurrentlyExtractable`...).
- Filtri `MailboxPath` (obbligatorio senza permesso Mailbox Global Query), `MessageNamePattern` (`*`), `MessageId`, `StartDateTime`/`EndDateTime` (`yyyy-mm-dd hh:mm:ss`), `MessageExtractable`; `OrderBy`/`Ascending`; pagine `QueryStartPos`/`QueryEndPos`, totale `QueryTotal`.
- `GetVisibilityData=Yes`: chi ha caricato (`AddedByProtocol`, `AddedByIP`, `AddedByWorkflowID`...) e tentativi di estrazione (`ExtractAttempt`).

### Mailbox Update Service
`MailboxUpdateServiceType` · `z-mailbox-update-service`
- `MessageId` obbligatorio; reimposta una sola regola di estraibilità. `ResubmitMessage=Yes` rimanda il messaggio al routing. Errori "Mailbox Message Not Found", "Mandatory Parameter Missing".

### Mailbox Correlate Document Service
`MailboxCorrelateDocumentServiceType` · `z-mailbox-correlate-document-service`
- Aggiunge al documento le correlazioni `Mailbox_MessageName`, `Mailbox_MessageId`, `Mailbox_MailboxPath`, per ritrovarlo nella ricerca per correlazione. Non controlla i permessi; nomi dei parametri di input non specificati dalla pagina. Errori "Message Not Found", "Invalid Mailbox Parameter".

### Mailbox Evaluate All Automatic Routing Rules Service
`MailboxEvaluateAllAutomaticRulesServiceType` · `z-mailbox-evaluate-all-automatic-routing-rules-service`
- Valuta i messaggi arrivati dopo il giro precedente; gira a schedule, disabilitato di default, `RuleId` obbligatorio in configurazione.
- **Ogni messaggio è valutato una volta sola**: se all'arrivo nessuna regola lo prende, non verrà ripreso nemmeno da una regola creata dopo (serve `ResubmitMessage`). Sopravvive a crash e riavvii.

## FTP e SFTP client

Retry, sessione unica, `TOKEN`, errori da riprovare: regole.md § Retry e connessioni FTP/SFTP.

### SFTP Client (suite)
GET `z-sftp-client-get-service` · PUT `z-sftp-client-put-service` · CD `z-sftp-client-cd-service` · Begin `z-sftp-client-begin-session-service` · End `z-sftp-client-end-session-service` · LIST `z-sftp-client-list-service` · DELETE `z-sftp-client-delete-service` · MOVE `z-sftp-client-move-service`
- **Comuni:** `SessionToken`; `ResponseTimeout` in s (sotto 30 diventa 30). `ServerResponse`: 0 OK, 2 No Such File, 3 Permission Denied, 4 General Failure, 6 No Connection, 7 Connection Lost.
- **Begin:** `SFTPClientAdapter`; `ProfileId` oppure `RemoteHost`/`RemotePort`/`RemoteUserId` + `RemotePasswd` o `UserIdentityKeyId`; `KnownHostKeyId`. I valori dello step prevalgono sul profilo. `ConnectionRetries` 1-50 (solo TCP/IP), `RetryDelay` minimo 100 s: `ResponseTimeout` deve superare il totale. I/O error: `sshTransportTimeout` in `sftp.properties`.
- **GET:** `RemoteFileName` **oppure** `RemoteFilePattern` (mai entrambi); più file = più documenti sotto `DocumentList`. `RetrieveErrorSetSuccess=YES` = Success anche in errore.
- **PUT:** documento da `DocumentList`, poi `DocumentId`, poi primario; `RemoteFileName` (default nome del documento).
- **CD:** `Directory` (`..` per salire, `CdUp` non supportato). **LIST:** `RemoteFileName` con un solo `*` (no `*text*`), output `Files` (`Name`, `Size`, `Type`, `ModificationTime`...). **MOVE:** `RemoteFromFileName`/`RemoteToFileName`, senza wildcard.

### FTP Client (suite)
PUT `l-ftp-client-put-service` · CD `l-ftp-client-cd-service` · Begin `l-ftp-client-begin-session-service` · End `l-ftp-client-end-session-service` · LIST `l-ftp-client-list-service` · GET `l-ftp-client-get-service` · DELETE `l-ftp-client-delete-service`
- **Comuni:** `SessionToken`, `ResponseTimeout` (in PUT/GET = inattività), `SaveTranscript`. `TranscriptDocumentId` = dialogo col server, la prima cosa da guardare.
- **Ogni risposta 4xx/5xx manda il BP in fault**, salvo GET con pattern e QUOTE.
- **Begin:** `FTPClientAdapter`, `RemoteHost`, `RemotePort`; `SSL` `SSL_NONE`/`SSL_EXPLICIT`/`SSL_IMPLICIT` (con `CACertificateId`).
- **PUT:** `ConnectionType` ACTIVE/PASSIVE, `RepresentationType` (BINARY default), `StoreAction` Normal/Append/Unique. Un BP con FTP client non va in Auto Resume (la sessione non c'è più).
- **GET:** `CheckFileSize=YES` va in errore se il file sta ancora crescendo (non con pattern); `RetrieveErrorSetSuccess`/`ListNamesErrorSetSuccess` ignorano il 550. **LIST:** `NamesOnly=YES` (NLST, `ListNames`). **CD:** `Directory` o `CdUp=YES`.

## HTTP, SOAP e REST

### HTTP Client (suite)
Begin `l-http-client-begin-session-service` · POST `l-http-client-post-service` · Method `l-http-client-method-service` · End `l-http-client-end-session-service`
- **Begin:** `HTTPClientAdapter`, `RemoteHost`, `RemotePort`; `SSL` None/Must (`CACertificateId`, `TLSVersion`); `ResetConnectionOnError`.
- **POST/Method** (`MethodType` solo Method): `URI`, `DocumentId`, `ResponseTimeout`, `RawRequest`, `RawResponse`, `ShowResponseCode` (codice HTTP prima riga del primario). **Lo stato è il codice HTTP, non 0/1.**
- Insidia: output di Get Document Info prima del POST sotto un nodo padre (es. `docInfo`): un `DocumentId` alla radice del ProcessData fa spedire il documento originale.

### HTTP Server Adapter / HTTP Respond Service
`HttpServerAdapter` `l-http-server-adapter` · `HttpRespondService` `l-http-respond-service`
- Server: un BP per `URI`; `User Authentication Required` default Yes; `Send Raw Messages` (default solo body); nel ProcessData `transport-instance-id`, `transport-session-id`, `http-method`, `http-request-uri`, parametri della query string.
- Respond: usa i due `transport-*`; `status-code` (default 200), `doc-has-headers` obbligatorio, `xport-doc-on-error`.

### SOAP Inbound / Outbound, REST API Client
- SOAP Inbound `z-soap-inbound-service`, Outbound `z-soap-outbound-service`: tipi di servizio `SOAInboundMsgProcessingService`/`SOARequestHandler` e `SOAOutboundMsgProcessingType` (pagine `z-soa-inbound-message-processing-service`, `z-soa-outbound-message-processing-service`, non riassunte). Inbound: `URI` anche nell'HTTP Server Adapter, BP diverso da `HandleSOAPRequest`, fault in `SOAPfaultcode`/`SOAPfaultstring`. Outbound: `ADD_SOAP_ENVELOPING`, `SOAP_ACTION`.
- REST API Client `RESTAPIClient` `z-rest-api-client-service`: `url`, `Rest Operation`, `Authorization` Basic/Bearer, `jsoninput1`, `headers` (`key:value,...`), `outputpath`; input JSON, output XML.

## File system

### File System Adapter
`File System` · `l-file-system-adapter`
- `Action` `FS_COLLECT` (`collectionFolder` → PrimaryDocument) / `FS_EXTRACT` (→ `extractionFolder`); percorsi relativi = working directory di Sterling.
- Insidie in lettura: `deleteAfterCollect` default **true**; in un BP senza `filter` legge **solo il primo file**; `noFilesSetSuccess` default false (nessun file = errore); `fileModTimeThreshold` 30 s salta i file appena scritti; `collectZeroByteFiles` default false.
- `collectMultiple=true` → `Document1..N`, con `concatenateFiles` default true (li unisce nel primario), `maxCollect`. `dbCollect=true` evita di raccogliere due volte lo stesso file.
- Scrittura: `appendOnExtract` (default sovrascrive), `assignFilename`/`assignedFilename` (`%^` = `nodename_yyyyMMddHHmmssSSS`; senza nome `nodename_<timestamp>.dat`), `subCharsOnExtract` (es. `:_`).
- Bootstrap: `initialWorkFlowId` per file (`maxThreads` 10), `userParm1..5` → `UserParm1..5`.

## Database

### Lightweight JDBC Adapter
`LightweightJDBCAdapterType` · `l-lightweight-java-database-connectivity-jdbc-adapter`
- `sql` con `?`, `pool`, `param1..20` + `paramtype1..20` (`String`, `Integer`, `Long`, `Double`, `Float`, `Date`, `Cursor`, `CharacterStream`, `CharacterStreamFromDocument`).
- `query_type` `SELECT` / `ACTION` (INSERT, UPDATE, DELETE) / `INSERT`, `UPDATE` (con i CharacterStream) / `PROCEDURE` (`{call Nome(?,?)}`, `paramDirection<n>` IN/OUT).
- Output nel **PrimaryDocument**: radice `result_name`, un `row_name` per riga; per le scritture `<Rows_Affected>`. `write_characterstream_to_document` (default YES) mette i campi lunghi in documenti separati.
- Retry al pool: `externalDBPoolRetries` (`noapp.properties`). Livello di compatibilita' del DB, nomi dei pool, commenti `--`, deadlock 1205, colonne = contratto: regole.md § SQL.

## Email

### SMTP Send Adapter
`SMTP_SEND_ADAPTER` · `z-smtp-send-adapter`
- `xport-smtp-mailhost`/`-mailport`, `-mailfrom`, `-mailto`, `-mailCC`, `-mailsubject`, `-mailsubjectencoding`, `xport-smtp-auth`, `xport-tp-ssloption`.
- `b2b-raw-message` false = documento come corpo text/plain; true = messaggio RFC822 completo (per gli allegati: MIME costruito prima). `b2bMailsvs.properties`: TLS 1.2 di default, `mail.smtp.timeout` se i thread restano appesi.

### B2B Mail Client Adapter
`B2B_MAIL_CLIENT_ADAPTER_OAUTH2_3` · `l-b2b-mail-client-adapter`
- POP3/IMAP, un BP per URI; solo configurazione (niente parametri da BPML). **Send Raw Messages** se a valle c'è Mail Mime. Header in `/ProcessData/Mail_Client/Headers/`. OAuth2: non specificato dalla pagina.

## Sistema e manutenzione

### Cache Refresh Service
`CacheRefreshServiceType` · `l-cache-refresh-service`
- Ricarica un file di property personalizzato letto da `sci-get-property`, senza riavvio; vale subito per tutte le istanze.
- `cache_name` = il tag di `sci-get-property('tag','chiave')`; `cache_type` = `Properties`.
- File cercato in: Customization UI (DB), `properties/<tag>.properties`, `properties/<tag>`, voce in `servers.properties`.
- **Insidia:** `sci-get-property` tiene in cache il file dalla prima lettura: dopo una modifica senza Cache Refresh si legge il valore vecchio. Non per le property di sistema.

### XAPI Service / Command Line Adapter 2
- XAPI `XAPI` `z-xapi-service`: chiama un'API interna (`api`, es. `getMaplist`), input `xml` (default il primario), `split`.
- CLA2 `CmdLine2` `l-command-line-adapter-2`: `cmdLine` (redirezioni solo in uno script), `parm0..9`, `useInput`/`useOutput`, `setSoTimeout` (60000 ms). **`successValue`** (0): senza un exit code corretto gli errori non si vedono. Output `CLA2/ProcessExitValue`.

### Servizi di sistema (non nei BP)
Index Business Process `l-index-business-process-service` (marca i BP per archive/purge) · BP Report `l-bp-report-service` · Backup BP `l-backup-business-process-service` · Purge BP Linkage `z-purge-business-process-linkage-service` · Auto Terminate `l-auto-terminate-service` (termina i BP Halted da più di 14 giorni, `bprecovery.properties`).

## EDI e altri servizi

Mappe: skill `sterling-mappe`.
- Translation `TranslationType` `adapters-translation-service`: `map_name`; **`ErrorIfAllDataNotConsumed` e `ErrorIfNoOutput` default false** (input non consumato o output vuoto senza errore); `output_to_process_data`, `validate_input`/`validate_output`; dettaglio nel translator report.
- EDIFACT Deenvelope `DeenvelopeEDIFACTType` `adapters-edifact-deenvelope-service`: dentro `EDIFACTDeenvelopeUnified`; `TRACKING_LEVEL` `none` toglie Correlation Search e Document Tracking.
- EDI Deenveloping `EDIDeenvelopeType` `adapters-edi-deenveloping-service`: separa gli interchange e lancia un BP per ciascuno; `ProcessInterchangesDespiteError` (no = uno non valido li ferma tutti). `BatchLikeTransactions`: regole.md § Routing e mailbox.
- Document Extraction `DocumentExtractionType` `adapters-document-extraction-service`: mappe di `DocExtractMapList` provate in ordine; output `DOC-SPLIT-n`, resto in `unrecognized`; `PDToProcessData`=No → array `SplitDocs` per For Each Document.
- EDI Encoder / EDI Enveloping / EDIFACT Envelope `adapters-edi-encoder-service`, `adapters-edi-enveloping-service`, `adapters-edifact-envelope-service`: il `Mode` dell'Encoder deve coincidere con quello dell'enveloping.
- EDIINT Pipeline `slsa-ediint-pipeline-service`, Acknowledge Check `slsa-ediint-acknowledge-check-service`, Header Scanning `slsa-ediint-header-scanning-service`: AS2 nei BP predefiniti; Ack Check attende l'MDN (`ACSPollInterval` 180 s) e con `ACSFailWFOnExpiredMessage` (Yes) manda in errore il BP senza MDN.
- Odette FTP `z-odette-ftp-adapter`; SOA Outbound Security `z-soa-outbound-security-service`; Check Expire `l-check-expire-service` e SAP TID Cleaner `z-sap-tid-cleaner-service` (BP di sistema schedulati).

## Concetti utili dei servizi

- Limitation policies FTP/SFTP `policies-ftp-sftp-adapter-limitation-overview`: solo adapter **server**, non client. Data Limit `policies-data-limit-overview`: KB al giorno condivisi da tutti gli utenti/IP della policy, il client può non mostrare l'errore. Anche `policies-command-limiting-overview`, `policies-bandwidth-limiting-overview`, `policies-lockout-overview`.
- FIFO `adapters-fifo-message-processing-enhancement`: solo JMS e MSMQ.
- Service Groups `services-service-groups`: configurazioni dello stesso tipo usate come un solo `participant` (bilanciamento, failover).
- Advanced Status dei servizi `adapters-advanced-status-messages-business-processes`; status report nel ProcessData `faqasa-how-do-i-retrieve-data-from-service-status-report`.
- Troubleshooting servizi `faqasa-what-are-some-troubleshooting-tips-services-in-business-processes`: configurazione modificata = vale per i processi nuovi; servizio disabilitato = BP fermo che riparte alla riabilitazione; servizio cancellato = Invalid Service.

## BPML

Regole (nomi, onFault, choice, loop, multiassign): regole.md.
- **assign** `elements-assign-activity`, `data-different-types-assigns`: in `output` da ProcessData al messaggio, in `input` dal messaggio al ProcessData. Costante nel `from` tra apici singoli (`from="'bar'"`). Output con **solo costanti**: il servizio ignora il mapping di output e non supporta quello di input.
- **choice** `activities-choice-activity`: esegue il primo `case` vero; nessuno vero = si prosegue dopo la choice. `negative="true"` nega la regola.
- **repeat** `elements-repeat-activity`: `ref` = attività complessa che contiene il repeat; senza condizione che cambia, ciclo infinito.
- **sequence** `activities-sequence-activity` (figli in ordine) · **all** `activities-all-activity` (in parallelo, finisce con l'ultimo).
- **spawn/join** `elements-join-spawn-activities`: `spawn ref` avvia un processo indipendente con copia del ProcessData; `join` aspetta solo i figli dello stesso processo; dialogo con `activities-produce-consume`.
- **onFault** `elements-onfault-element`, `oe-when-fault-code-does-not-match-onfault-code`: più onFault con `code` diversi, uno solo senza; codice non trovato a un livello = si risale fino a un onFault senza codice, se manca il BP va in Halted. IBM sconsiglia `join` annidati con onFault.
- **operation** `activities-operation-activity`, `elements-input-output`: unico modo di chiamare un servizio; `participant` obbligatorio, `output` prima di `input`.
- **message_to_child** `models-business-process-model-validation`: messaggi della validazione "Document loop contains an InvokeBusinessProcess service without an assign to message_to_child" / "message_to_child not guaranteed to be released"; correzione in regole.md § Best practice IBM.
- **ProcessData** `bpml-what-is-process-data`, `data-tips-accessing-content`: XML che cresce con il BP; ogni servizio lavora su ProcessData + primario; dati da un primario non XML: mappa per XML Encoder.
- **Persistenza** `options-business-process-persistence`: Full, Step Status - Engine May Override (consigliato), BP Start Stop - EMO, System Default, Step Status Only, BP Start Stop Only, Zero (solo avvio sincrono), Error Only, BP Start Stop Only (No Errors) (**errore non salvato, BP resta ACTIVE**), Override None No IC. Gli override per step nel BPML prevalgono.
- **Opzioni del BP** `options-business-process-levels`: Set Queue (4); senza BP Queuing persistenza Zero e niente restart; **Enable Transaction** non con Begin/End Transaction nel BP (fallisce), "Commit All Steps when there is an error" default true. Life span `options-business-process-life-span`: System Default 2 giorni.

## Monitoraggio e troubleshooting

- `monitoring-advanced-status-messages`: azioni per Service Disabled, Service Error, Invalid Service, Mandatory parameter missing, Invalid value, BP Disabled.
- `troubleshooting-restarting-resuming-business-process-instances`: Resume = dall'ultimo step persistito, stesso ID (errore di servizio); Restart = nuova istanza, stesso documento; Advanced Restart = stesso documento con un altro BP (errore nel BPML).
- `indicators-status-indicator-red-light`: cosa fare per stato; Halted non viene archiviato né purgato finché non si termina. `troubleshooting-terminating-restarting-business-process`: Troubleshooter > Business Process Usage.
- `troubleshooting-resolving-persistence-errors`: BP Start/Stop + servizio Force None + errore in quello step = BP che resta active.
- `troubleshooting-resolving-business-subprocess-errors`, `processes-what-happens-subprocesses-when-i-terminate-process` (terminare il padre manda in Halted i figli che lo continuano), `ttyp-why-is-linkage-information-between-parent-subprocess-lost`, `instance-view-process-data-single-step-in-process`.

## Pagine IBM chiave

`adapters-sterling-b2b-integrator-services-l`, `adapters-sterling-b2b-integrator-services-m-z` (indici dei servizi), `adapters-retired-services`, `bpml-process-activities-elements`, `processes-business-process-modeling-best-practices`, `management-servicesadapters-that-support-transactional-processing`, `processes-business-process-troubleshooting`.

## Non trattati qui

JMS/MQ/Kafka, adapter ERP, Connect:Direct, EBICS, adapter cloud, LDAP, Global Mailbox, Script Adapter, Dynamic Services e i comandi FTP/SFTP non elencati: vedere gli indici dei servizi IBM (Pagine IBM chiave).
