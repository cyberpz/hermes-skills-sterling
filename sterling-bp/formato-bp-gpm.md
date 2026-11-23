# Formato del file .bp (GPM) di Sterling B2B Integrator

Com'e' fatto un `.bp` esportato dal Graphical Process Modeler, dove sta a DB e cosa serve per generarne uno da un BPML.

## Il file .bp

- Il `.bp` esportato e' uno **zip** con due file: `stercomm.bpml` (il codice) e `stercomm.gpl` (il diagramma). Entrambi
  XML UTF-8 con fine riga LF. **Un BPML di solo testo rinominato `.bp` viene rifiutato** all'upload ("non valido").
- Per caricare un BP scritto a mano serve quindi anche il `.gpl`: `crea_bp.py` lo genera dal BPML e impacchetta lo zip.

## Dove sta a DB

- `WFD_XML.XML` -> `DATA_TABLE` = BPML (gzip, pagine `PAGE_INDEX` da concatenare).
- `WFD_XML.GBMDATA` -> `DATA_TABLE` = gzip di un oggetto Java serializzato (`com.sterlingcommerce.woodstock.ui.BPFile`)
  che contiene lo stesso zip del `.bp`: si estrae cercando la firma `PK\x03\x04` fino alla fine della directory
  centrale (`PK\x05\x06` + 22 byte + lunghezza del commento). Lo zip estratto cosi' e' identico byte per byte a
  quello esportato dal GPM (`Export-SterlingSource.ps1` fa questo).
- Le versioni caricate come testo, senza GPM, non hanno `GBMDATA`: di quelle si ricava solo il BPML.
- Versione attiva: `WFD_VERSIONS.DEFAULT_VERSION`; commento della versione: `WFD.DESCRIPTION`.

## Struttura del .gpl

- Radice `<GPL language="BPML" ...>`, un `<GPLNODE>` per attivita' con `ACTIVITYID` numerico unico, `ACTIVITY` = tipo,
  `INSTANCENAME`, `NODECLASS` (1/3 start, 4 end, 5 operazione, 6 struttura), e dentro `ACTIVITYDATA` che ripete i dati
  del BPML (`<field>`/`<value>`; negli assign `from` = espressione, `constant` = testo fisso).
- Archi: `<GPLEDGE><GPLEDGEID>` punta al nodo successivo.
- Regole (`<rule>`): nel nodo Start come `Rule_Config`.
- Sequenza: nodo `Sequence_Start_Activity` -> primo figlio, ultimo figlio -> `Sequence_End_Activity` -> nodo dopo la
  sequenza.
- Choice: un arco per case con `GPLEDGENAME` = `<regola>..` e `GPLEDGESTATE` = `<case activity=... ref=...
  negative='false' />`; la fine di ogni case -> `Choice_End_Activity`.
- Repeat: `Repeat_Activity` con `ref`.
- **onFault**: il nodo inizio della sequenza che lo possiede ha un secondo arco verso il suo `OnFault Start`; i nodi
  dell'onFault stanno in un `GPLLAYOUT` a parte (`GROUPID` = id di un `GPLGROUPLAYOUTVIEW TYPE="ONFAULT"` nel layout
  padre).
- Ogni nodo ha una sola `GPLNODEVIEW` (coordinate) in un layout.

## Dettagli per generare un .gpl da un BPML

Ricavati da `.gpl` esportati dal GPM; un generatore che li segue rigenera gli stessi nodi, archi e layout.
- **Nodo operazione**: `ACTIVITY` = tipo del servizio, non il participant (`AssignService` -> `AssignServiceType`,
  `WaitService` -> `WaitServiceType`, `DocumentKeywordReplace` -> `DocKeywordReplace`, `SleepService` ->
  `SleepService`): si prende da un gpl esistente con lo stesso participant (`activity_map.json` contiene quelli
  standard). `SERVICEOPERATION` = `ProcessData`; `SERVICEMESSAGE` vuoto oppure il nome del messaggio di output
  (indifferente).
- `inputMessageMode` = `2` se l'input contiene `assign to="." from="*"`, altrimenti `1`; `outputMessageMode` = `3` se
  `. <- *` e' il primo assign dell'output, `4` se e' l'ultimo.
- **Subflow** (sequence disegnata come riquadro che si apre): `Sequence_Start/End_Activity` con `ACTIVITY` vuoto e
  `INSTANCENAME` `Start`/`End`, viste `SFSTART`/`SFEND` in un `GPLLAYOUT` col nome della sequence; nel layout padre un
  `GPLLAYOUTVIEW ID=<id layout> TYPE="SUBFLOW"`. Gli archi puntano comunque ai nodi Start/End del subflow.
- **onFault**: `OnFault_Start_Activity` (`ACTIVITY` vuoto) -> contenuto -> `OnFault_End_Activity` (nessun arco), viste
  `OFSTART`/`OFEND`; gli id dei gruppi (`GROUPID` / `GPLGROUPLAYOUTVIEW ID`) hanno una numerazione a parte da quella
  dei layout. Negli onFault esportati il contenuto e' sempre una `sequence`. Il `code` dell'onFault va scritto nei
  dati del nodo `OnFault Start`: se manca, il GPM al salvataggio rigenera un `<onFault>` senza codice, che intercetta
  tutti gli errori.
- **Nodo Start**: `Process_Activity`, `ACTIVITY` vuoto, `NODECLASS` 3 (1 nei gpl piu' vecchi); **End**:
  `ACTIVITYDATA name=""`, classe 4.

## Verifica

- Un gpl generato e aperto nel GPM, riordinato e riesportato non mostra differenze di struttura (nodi, archi, dati):
  il GPM cambia solo le coordinate. Per controllarlo: `gplcompare.py <gpl_a> <gpl_b>`.
- Dopo il caricamento aprire il BP nel GPM e controllare che diagramma e sorgente coincidano; poi riesportare la
  versione salvata e confrontare il BPML con la bozza (il GPM rigenera il BPML dal diagramma).
- Per caricare un BP scritto a mano partendo da uno simile: `crea_bp.py --like <bp simile>` riusa subflow e tipi di
  participant dell'originale; controllare che ogni arco punti a un nodo esistente e che il grafo ripercorra la
  struttura del BPML (lo fa `crea_bp.py`).
