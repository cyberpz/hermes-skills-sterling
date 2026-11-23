# Sterling-Skills

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

## Installazione

Le skill sono markdown con frontmatter YAML (formato Agent Skills): lo stesso identico file
funziona su Hermes Agent e su Claude / Claude Code.

**Claude Code** — personali (tutti i progetti):

```bash
cp -r sterling-bp sterling-mappe sterling-edi-ops sterling-map-compile ~/.claude/skills/
```

**Claude Code** — solo questo progetto (versionate nel repo del progetto):

```bash
mkdir -p .claude/skills
cp -r sterling-bp sterling-mappe sterling-edi-ops sterling-map-compile .claude/skills/
```

**Claude (app claude.ai)** — Settings → Capabilities → Skills: zippare ogni cartella
(`zip -r sterling-bp.zip sterling-bp/`) e caricarla.

**Hermes Agent**:

```bash
cp -r sterling-bp sterling-mappe sterling-edi-ops sterling-map-compile ~/.hermes/skills/
```

## Riferimenti esterni usati

- IBM Sterling Map Editor Guide — "Compiling Maps Using the Command Line"
- IBM Sterling extended rule language reference (funzioni stringa disponibili)

## Licenza

MIT.
