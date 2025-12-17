Ottenere le credenziali corrette è il passaggio più delicato. Confluence Cloud utilizza un sistema di **API Token** (che sostituisce la password classica per motivi di sicurezza).

Ecco la guida passo-passo per popolare il tuo file `.env`.

---

###1. CONFLUENCE_URLÈ l'indirizzo base della tua istanza Atlassian.

* **Formato:** `https://nome-azienda.atlassian.net`
* **Nota:** Non aggiungere `/wiki` o altre sottocartelle alla fine, lo script gestisce i percorsi internamente.

###2. CONFLUENCE_USERÈ l'indirizzo **email** associato al tuo account Atlassian (quello che usi per fare il login).

###3. CONFLUENCE_TOKEN (API Token)Non devi usare la tua password. Devi generare un token specifico:

1. Vai su [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens).
2. Clicca su **Create API token**.
3. Assegna un'etichetta (es: "Confluence Backup Script").
4. **Copia il token immediatamente** (non potrai più visualizzarlo, dovrai rigenerarlo se lo perdi).

###4. PARENT_PAGE_IDQuesto è l'ID della pagina "madre" da cui vuoi iniziare lo scaricamento ricorsivo.
Esistono due modi per trovarlo:

* **Metodo URL:** Apri la pagina su Confluence. Guarda l'URL nel browser. L'ID è il numero che compare dopo `pageId=` o nell'ultima parte dell'indirizzo.
* *Esempio:* `.../wiki/spaces/DS/pages/12345678/Titolo+Pagina` -> L'ID è **12345678**.


* **Metodo Info Pagina:** Sulla pagina Confluence, clicca sui tre puntini (**...**) in alto a destra e seleziona **Page Information**. L'ID sarà visibile nell'URL della pagina informativa o nei dettagli tecnici.

---

###Esempio di file `.env` pronto:```env
CONFLUENCE_URL=https://mia-azienda.atlassian.net
CONFLUENCE_USER=mario.rossi@email.it
CONFLUENCE_TOKEN=ATATT3xFfGF0...[codice lungo]
PARENT_PAGE_ID=987654321

```

---

###Un piccolo consiglio sulla sicurezzaSe stai lavorando in un ambiente condiviso, assicurati che il file `.env` abbia permessi ristretti sul tuo computer locale:

```bash
chmod 600 .env

```