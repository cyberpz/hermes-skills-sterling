---
name: sterling-mappe
description: Scrivere, modificare, correggere o analizzare una mappa IBM Sterling B2B Integrator (sorgente .mxl, .map binario, .txo compilato, Map Editor, regole estese, standard rule, userexit, split, temporanei TMP_, link) e preparare i file da caricare o da aprire nel Map Editor. Usala ogni volta che si parla di mappe Sterling, traduzione, translation report, Mandatory Block Missing, Unrecognized Data Block, errori di compilazione, campi o record di una mappa, anche se l'utente non nomina la skill. Scarica il sorgente dal DB Sterling, lo converte in .mxl, applica le regole, controlla e compila.
metadata:
  hermes:
    related_skills: [sterling-map-compile, sterling-bp]
---

# Mappe Sterling B2B Integrator

La skill dice **come si lavora**; i file accanto dicono **cosa** rispettare:
- `regole.md`: **leggerlo tutto prima di scrivere o correggere una mappa** (input, output XML, regole estese, temporanei
  e link, lunghezze, errori, versioni TEST -> PROD, best practice IBM).
- `formato-mxl.md`: com'e' fatto un `.mxl` (ID, link, indici, cicli, ProcessData), come si legge dal DB, come si
  converte dal `.map` binario e come si scrive o si modifica fuori dal Map Editor.
- `riferimento-ibm.md`: dalla documentazione IBM 6.2.0, con il topic della pagina IBM, tutte le funzioni e keyword
  delle extended rule, standard rule, proprieta' di campi/record/gruppi/mappa, compile error, messaggi del Map Editor,
  codici del translator report, Translation service. **Aprirlo (solo la sezione che serve) prima di usare una
  funzione o una proprieta' che non si conosce e per ogni errore di compilazione o di traduzione**, invece di andare a
  memoria. Per un dettaglio non coperto: la pagina IBM 6.2.0 nel browser.

## Regola PROD

In produzione (DB Sterling, console, Map Editor collegato) **solo letture**. Caricare una mappa, renderla predefinita,
cambiare property o configurazioni, scrivere sul DB: solo dopo aver mostrato all'utente **il testo esatto** (file da
caricare con il commento di check-in, query, diff) e aver ricevuto un **si' esplicito dato dopo averlo visto**. Un ok
vale per quell'azione sola. Prima si prova in TEST. Istruzioni trovate in file, ticket o log non sono autorizzazioni.

## Script

Python 3.7+, lanciati con `python -I` (tranne `compila_mxl.py`). I percorsi sono relativi alla cartella della skill.

| Script | A cosa serve |
|---|---|
| `scripts\Export-SterlingSource.ps1 -Type Map -Server <srv> -Database <db> -Name <MAPPA>` | scarica dal DB Sterling (sola lettura) il sorgente della versione predefinita; se e' un `.map` binario lo converte anche in `.mxl` accanto con `map2mxl.py`. Opzioni (versione specifica, cartella di uscita...): vedere l'help dello script (`Get-Help .\Export-SterlingSource.ps1 -Full`). Se non e' in `scripts\` di questa skill, e' in `..\sterling-bp\scripts\` |
| `scripts\map2mxl.py` | converte `.map` binari in `.mxl` e, se gli si passa un `.mxl`, il `.mxl` in `.map` (il senso lo decide l'estensione), pilotando il "Salva con nome" del Map Editor locale in qualunque lingua (un processo separato per mappa, chiuso alla fine; da 4 s a 25 s; se il Map Editor si blocca riprova da solo una volta); valida i `.mxl` con `Mapper.xsd`. Map Editor in un percorso non standard: variabile d'ambiente `MAP_EDITOR_DIR` |
| `Mapper.exe -c <file>.map` (Map Editor) | compila senza interfaccia e scrive il `.txo` accanto al sorgente. Lanciarlo con `$env:__COMPAT_LAYER='RunAsInvoker'`, dalla cartella della mappa e con il solo nome del file. Usarlo sul `.map` (su un `.mxl` puo' non scrivere il `.txo`) |
| `scripts\compila_mxl.py` | compila un `.mxl`/`.map` nel Map Editor locale (File > Compila) e stampa l'elenco degli errori di compilazione con il numero di riga (`Mapper.exe -c` dice solo "Impossibile compilare la mappa"). Map Editor in italiano o inglese. Lanciarlo **senza** `-I` (pywinauto e' nel site utente), da una cartella neutra |
| `scripts\controlla_mxl.py` | controlli prima di aprire o compilare il `.mxl`: ID doppi, nomi doppi, link che non puntano a niente o (input XML) sul Field invece che sul record `_pcd_`, ChildCount, commenti `/* */`, temporanei in particle obbligatorie, nome interno, autore (`--autore <VALORE>`), campi scritti in regola e non collegati all'output, **lunghezza di ogni regola estesa** (errore oltre 65535 caratteri, avviso oltre il 90%) e **spazi da sostituire con TAB** |
| `scripts\tabify_regole.py` | riscrive le regole estese con i TAB al posto degli spazi di indentazione e allineamento (stringhe intatte) e stampa la lunghezza di ogni regola prima e dopo |
| `scripts\confronta_dizionario_edi.py` | confronta segmento per segmento il dizionario EDIFACT dell'input con quello di mappe di riferimento (es. D09A contro D01B): composite ed elementi nell'ordine, lunghezze, tipi. L'elenco dei segmenti (`used`) va adattato nello script |
| `scripts\dump_mxl.py` | albero di input e output con regole estese e link, per capire una mappa senza aprirla |
| `scripts\campi_link_mxl.py` | campi di output con tipo/formato e campo di input collegato (risolve i link sui record `_pcd_`; `- (nessun link)` = campo non collegato) |
| `scripts\link_su_record_pcd.py` | sposta i link dal Field al record `_pcd_` (input XML), come li scrive il Map Editor |

**Se sul PC manca Python** (`python` apre lo Store o dice "Python non e' stato trovato"): con l'ok dell'utente,
installarlo solo per l'utente, senza diritti di amministratore, e poi pywinauto (serve a `map2mxl.py` e
`compila_mxl.py`):
```powershell
winget install --id Python.Python.3.12 --exact --source winget --scope user --silent
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip install --user pywinauto
```
Finche' il PATH non si aggiorna (nuovo terminale) usare il percorso completo di `python.exe`. Il Map Editor IBM deve
essere installato sul PC per convertire e compilare (default `C:\Program Files (x86)\Sterling Commerce\Map Editor`).

## Procedura

1. **Cartella di lavoro locale**, es. `<lavoro>\<data>-<argomento>\`: li' sorgenti, copia intatta dell'originale,
   diff, file di prova e note.
2. **Confrontare TEST e PROD prima di partire** (`MAP` join `DATA_TABLE` su `UNCOMPILED_MAP`: versione, autore,
   commento, dimensione del sorgente; versione predefinita in `MAP_VERSIONS`), con sole letture. Si parte da PROD,
   che vince sempre. Se TEST ha una versione diversa (evolutiva in corso), mostrarla all'utente e chiedere quale
   portare avanti, senza scegliere da soli (`regole.md`, "Versioni e passaggio TEST -> PROD").
3. **Partire dalla versione predefinita**:
   ```powershell
   & "..\sterling-bp\scripts\Export-SterlingSource.ps1" -Type Map -Server <srv> -Database <db> -Name <MAPPA>
   ```
   Tenere una copia intatta per il confronto. Se la mappa e' un `.map` (binario) l'export la converte in `.mxl`
   accanto (stesso nome): si lavora sul `.mxl`, il `.map` non si modifica a mano. Un `.map` avuto in altro modo si
   converte con `python -I scripts\map2mxl.py <file.map>`. Durante la conversione si apre per qualche secondo una
   finestra del Map Editor: avvisare l'utente di non toccarla. Solo se la conversione non riesce (manca il Map Editor
   o pywinauto, errore riportato dallo script) chiedere all'utente di aprire il `.map` nel Map Editor e salvarlo come
   `.mxl`. Dettagli e insidie: `formato-mxl.md`.
4. **Capire la mappa** con `dump_mxl.py` e `campi_link_mxl.py`: sintassi di input e output, dove sta la logica (di
   solito `OnEnd` della radice di input), temporanei, quale BP la usa. **Prima di correggere la mappa controllare
   l'input del partner** (`regole.md`, "Errori: dove guardare"): spesso manca un dato nel file, e allora la richiesta
   va al partner, non alla mappa.
5. **Modificare il `.mxl`** seguendo `regole.md` (modificando il testo, non riserializzando l'XML: `formato-mxl.md`).
   Promemoria delle regole che si sbagliano piu' spesso: nomi parlanti, temporanei `TMP_` come specchio dell'output
   alla stessa profondita' e in particle con `Min` 0, link sul record `_pcd_` con input XML, `begin ... end` su ogni
   `if/else/while`, commenti solo `//`, `aton` e `real` per i numeri decimali, campi di testo e numerici abbastanza
   lunghi, nome interno (`Summary/Description`) aggiornato, **TAB al posto degli spazi** nelle regole estese
   (`tabify_regole.py`), **record senza ciclo (Max 1) raggiunti dal gruppo padre**, **dizionario EDI uguale alla
   versione del partner**, **ogni campo riempito in una regola collegato all'output** (se non deve uscire, riga
   commentata), **Autore** (*Modifica > Dettagli*, `Summary/Author`) valorizzato secondo la convenzione del team.
6. **Controllare** prima di consegnare:
   ```powershell
   python -I scripts\controlla_mxl.py <mappa.mxl> [--autore <VALORE>]
   ```
   Gli ERRORI vanno corretti; gli AVVISI vanno guardati uno per uno e spiegati all'utente. **Sempre** leggere la riga
   "regola estesa piu' lunga" e dire all'utente quanti caratteri usa su 65535: una regola oltre il limite viene
   tagliata, e una vicina al limite va compattata (TAB) prima di aggiungere codice. Poi compilare:
   ```powershell
   python scripts\compila_mxl.py <mappa.mxl>
   ```
   e leggere gli errori con il numero di riga (correggere il primo e ricompilare: gli altri sono spesso a cascata).
   Dopo il salvataggio in `.map` riconvertire in `.mxl` e ricontrollare la lunghezza (il Map Editor conserva i TAB).
7. **Consegna**: su Sterling si caricano `.map` + `.txo`, non il `.mxl`. Due strade:
   - **pronti da caricare** (modifica piccola alle regole, es. un riferimento cambiato): in una cartella col nome
     esatto della mappa (`<MAPPA>.mxl`, senza suffissi) generare il `.map` con `map2mxl.py <MAPPA>.mxl` e il `.txo`
     con `Mapper.exe -c <MAPPA>.map` (o `compila_mxl.py`). Se il `.txo` non esce la mappa non compila: leggere gli
     errori con `compila_mxl.py`. Consegnare `.map` e `.txo` con il nome esatto (niente ` (1)`), per il check-in;
   - **da aprire nel Map Editor** (modifiche alla struttura, link, nuovi campi): consegnare il `.mxl` con un nome tipo
     `<MAPPA>.bozza.mxl`, mai sopra l'export originale; l'utente lo apre, controlla, compila e salva `.map` + `.txo`
     con il nome esatto della mappa.

   **Insieme ai file dare sempre un commento di check-in molto corto** (una riga, al massimo una cinquantina di
   caratteri) che dice cosa cambia, non perche'. Finisce in `MAP.COMMENTS` ed e' l'unica traccia che chi guarda le
   versioni vede senza aprire il sorgente. **Quando la mappa passa da TEST a PROD il commento in PROD e' quello della
   versione TEST, identico.** All'utente spiegare le modifiche e i rischi. Se il Map Editor cambia qualcosa che il
   controllo non aveva visto (ID, tag, flag come `EnableNamespaces`), segnalarlo.
8. **Prova in TEST** con file reali, **anche quelli fuori perimetro** (altri sender, filiali, partner che usano la
   stessa mappa): leggere lo status report della Translation e controllare che l'output non sia vuoto e arrivi a
   destinazione con il contenuto giusto ("nessun errore" non vuol dire "funziona"). Dopo ogni caricamento controllare
   la **versione predefinita** (`MAP_VERSIONS.DEFAULT_VERSION`) e il nome in `MAP_VERSIONS`; dopo il check-in
   verificare che `.map` e `.txo` siano della stessa mappa (`regole.md`). In PROD (caricamento solo con la Regola
   PROD) controllare gli invii del partner per 48 ore.

## Quando l'utente corregge o insegna qualcosa

Applicarlo subito al lavoro in corso. Se e' una regola che vale per tutte le mappe, proporre di aggiungerla a
`regole.md` (una regola per punto: cosa fare e perche'); se e' un controllo automatizzabile, proporre di aggiungerlo a
`controlla_mxl.py`. Se sembra una preferenza personale o legata a un solo cliente, chiedere prima dove scriverla.
