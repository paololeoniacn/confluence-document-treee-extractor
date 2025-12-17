#📘 Confluence PDF ExporterUn tool basato su **Podman** e **Python** per scaricare ricorsivamente intere gerarchie di pagine da Confluence Cloud e convertirle automaticamente in documenti **PDF**.

##🚀 Caratteristiche* **Esportazione Ricorsiva**: Scarica la pagina indicata e tutte le sue sottopagine.
* **Conversione PDF**: Trasforma l'HTML di Confluence in file PDF leggibili offline.
* **Organizzazione Automatica**: Crea una struttura di cartelle speculare a quella di Confluence.
* **Ambiente Isolato**: Funziona dentro un container (Podman), senza sporcare il tuo PC con dipendenze Python.

---

##🛠️ Requisiti Preliminari1. **Podman** installato e avviato.
2. Un **API Token** di Atlassian ([Generalo qui](https://id.atlassian.com/manage-profile/security/api-tokens)).
3. L'**ID della pagina** iniziale (lo trovi nell'URL di Confluence).

---

##⚙️ ConfigurazioneCrea un file chiamato `.env` nella cartella principale e compila i tuoi dati:

```env
CONFLUENCE_URL=https://tua-azienda.atlassian.net
CONFLUENCE_USER=tua-email@azienda.it
CONFLUENCE_TOKEN=tuo_api_token_segreto
PARENT_PAGE_ID=123456789

```

---

##📖 Utilizzo (Lanciatore Bash)Abbiamo creato uno script `conf-down.sh` per gestire tutto con comandi semplici:

| Comando | Descrizione |
| --- | --- |
| `./conf-down.sh build` | Costruisce l'immagine del container (da fare al primo avvio). |
| `./conf-down.sh start` | Avvia il test di connessione e il download dei PDF. |
| `./conf-down.sh status` | Verifica se il container o l'immagine sono presenti. |
| `./conf-down.sh clean` | Rimuove container e immagini per liberare spazio. |
| `./conf-down.sh clean all` | Rimuove tutto, **inclusi i PDF scaricati**. |
| `./conf-down.sh bash` | Entra in modalità terminale dentro il container (debug). |

---

##📁 Struttura OutputDopo l'esecuzione, troverai i file nella cartella `./output`:

```text
output/
└── Titolo Pagina Radice/
    ├── Titolo Pagina Radice.pdf
    └── Sottopagina 1/
        ├── Sottopagina 1.pdf
        └── Sottopagina 1.1.pdf

```

---

##⚠️ Risoluzione Problemi* **Errore DNS**: Se il container non raggiunge internet, lo script `conf-down.sh` è già configurato per forzare i DNS di Google (`8.8.8.8`).
* **Pagine Mancanti**: Assicurati che l'utente associato all'API Token abbia i permessi di lettura per l'intero spazio Confluence.
* **Qualità PDF**: Tabelle estremamente complesse o Macro dinamiche potrebbero subire variazioni di layout nel passaggio a PDF.

---

##🛠️ SviluppoSe modifichi il codice Python, ricordati di rigenerare l'immagine:

```bash
./conf-down.sh clean
./conf-down.sh build

```