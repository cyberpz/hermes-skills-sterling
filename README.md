# hermes-skills-sterling

Skill condivisibili per operazioni su **IBM Sterling B2B Integrator** e integrazione EDI,
scritte come [Hermes Agent skills](https://hermes-agent.nousresearch.com/docs) (markdown + YAML frontmatter, riutilizzabili con qualsiasi agente che supporti skill in questo formato).

Contenuto generalizzato da lavoro operativo reale: nessuna informazione di cliente, partner,
credenziale, host o percorso interno.

## Contenuto

| Skill | Copertura |
|---|---|
| `sterling-edi-ops` | Ombrello operativo: triage log-archive, tuning code BusinessProcess, mappe MXL, estensioni web WAR su Sterling, integrazione Amazon SP-API senza SDK, feed catalogo/PRICAT per partner |
| `sterling-map-compile` | Compilazione headless di mappe Sterling (`.mxl`/`.map` → `.txo`) con `mapper.exe -c` sotto Wine, senza GUI |

## Installazione (Hermes Agent)

Copiare le cartelle delle skill nella directory skills dell'agente, ad es.:

```bash
cp -r sterling-edi-ops sterling-map-compile ~/.hermes/skills/
```

## Riferimenti esterni usati

- IBM Sterling Map Editor Guide — "Compiling Maps Using the Command Line"
- IBM Sterling extended rule language reference (funzioni stringa disponibili)
- Amazon SP-API developer docs (`llms.txt` index) + OpenAPI models su GitHub

## Licenza

MIT.
