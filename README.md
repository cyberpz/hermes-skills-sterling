# hermes-skills-sterling

Skill condivisibili per operazioni su **IBM Sterling B2B Integrator** e integrazione EDI,
scritte come [Hermes Agent skills](https://hermes-agent.nousresearch.com/docs) (markdown + YAML frontmatter, riutilizzabili con qualsiasi agente che supporti skill in questo formato).

Contenuto generalizzato da lavoro operativo reale: nessuna informazione di cliente, partner,
credenziale, host o percorso interno.

## Contenuto

| Skill | Copertura |
|---|---|
| `sterling-bp` | Scrivere/correggere Business Process (BPML, `.bp`/`.gpl`, GPM): regole strutturali, onFault, transazioni, retry FTP/SFTP, export dal DB, workflow TEST→PROD |
| `sterling-mappe` | Scrivere/correggere mappe Sterling (`.mxl`/`.map`/`.txo`) su Windows con Map Editor locale: conversione, controlli (`controlla_mxl.py`), compilazione, regole estese |
| `sterling-edi-ops` | Ombrello operativo: triage log-archive, tuning code BusinessProcess, mappe MXL, estensioni web WAR su Sterling |
| `sterling-map-compile` | Compilazione headless di mappe (`.mxl`/`.map` → `.txo`) con `mapper.exe -c` sotto **Wine/Linux**, senza GUI — gemello via-Wine di `sterling-mappe` |

## Installazione (Hermes Agent)

Copiare le cartelle delle skill nella directory skills dell'agente, ad es.:

```bash
cp -r sterling-edi-ops sterling-map-compile ~/.hermes/skills/
```

## Riferimenti esterni usati

- IBM Sterling Map Editor Guide — "Compiling Maps Using the Command Line"
- IBM Sterling extended rule language reference (funzioni stringa disponibili)

## Licenza

MIT.
