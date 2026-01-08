import os
import sys
import urllib3 
from atlassian import Confluence
from xhtml2pdf import pisa

# Disabilita i warning SSL (necessario per rete interna aziendale)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Caricamento variabili d'ambiente
# --- 1. CONFIGURAZIONE CON PULIZIA INPUT ---

def get_env_var(name, default=None):
    """Recupera la variabile e la pulisce da stringhe 'None' o spazi extra."""
    val = os.getenv(name, default)
    if val is None or str(val).lower() in ("none", ""):
        return None
    return str(val).strip()

# Caricamento e pulizia
URL = get_env_var("CONFLUENCE_URL")
# Rimuoviamo lo slash finale dall'URL se presente per evitare URL malformati (es. //rest/)
if URL:
    URL = URL.rstrip('/')

USERNAME = get_env_var("CONFLUENCE_USER")
API_TOKEN = get_env_var("CONFLUENCE_TOKEN")
SPACE_KEY = get_env_var("SPACE_KEY")
PARENT_PAGE_ID = get_env_var("PARENT_PAGE_ID")

def convert_html_to_pdf(source_html, output_filename):
    """Converte una stringa HTML in un file PDF."""
    with open(output_filename, "w+b") as result_file:
        # pisa.CreatePDF trasforma l'HTML in PDF
        pisa_status = pisa.CreatePDF(source_html, dest=result_file, encoding='utf-8')
    return not pisa_status.err

def clean_filename(title):
    """Rimuove caratteri non validi per i nomi dei file."""
    return "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()

def download_recursive(confluence, page_id, path, level=0):
    try:
        # Recuperiamo la pagina con il corpo storage
        page = confluence.get_page_by_id(page_id, expand='body.storage')
        title = clean_filename(page['title'])
        html_raw = page['body']['storage']['value']
        
        # CSS minimo per evitare che le tabelle escano dal foglio
        # CSS ottimizzato per tabelle grandi e lunghe
        full_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ 
                    size: a4; 
                    margin: 1cm; 
                }}
                body {{ 
                    font-family: Helvetica; 
                    font-size: 9pt; 
                }}
                /* Forza la tabella a dividersi tra le pagine */
                table {{ 
                    -pdf-keep-with-next: false;
                    border-collapse: collapse; 
                    width: 100%; 
                    word-wrap: break-word;
                }}
                td, th {{ 
                    border: 1px solid #ccc; 
                    padding: 4px; 
                    vertical-align: top;
                }}
                /* Evita che immagini giganti rompano il layout */
                img {{ 
                    max-width: 100%; 
                    height: auto; 
                }}
            </style>
        </head>
        <body>
            <h1 style="color: #0052cc;">{page['title']}</h1>
            <hr>
            {html_raw}
        </body>
        </html>
        """
        
        current_path = os.path.join(path, title)
        os.makedirs(current_path, exist_ok=True)
        
        pdf_path = os.path.join(current_path, f"{title}.pdf")
        
        if convert_html_to_pdf(full_html, pdf_path):
            print(f"{'  ' * level}✔ Creato: {title}.pdf")
        
        # RICORSIONE: Cerchiamo i figli di questa specifica pagina
        children = confluence.get_page_child_by_type(page_id, type='page')
        for child in children:
            download_recursive(confluence, child['id'], current_path, level + 1)
            
    except Exception as e:
        print(f"[WARN] Errore sulla pagina {page_id}: {e}")


def main():
    if not URL or not API_TOKEN:
        print("[ERROR] URL o TOKEN mancanti.")
        sys.exit(1)

    try:
        # Pulizia URL
        clean_url = URL.strip().rstrip('/')

        # Inizializzazione basata sulla documentazione ufficiale
        if USERNAME:
            print(f"[AUTH] Modalità Basic Auth (Cloud): {USERNAME}")
            confluence = Confluence(
                url=clean_url,
                username=USERNAME,
                password=API_TOKEN,
                cloud=True,
                verify_ssl=False
            )
        else:
            print("[AUTH] Modalità Personal Access Token (PAT)")
            # Nota: verify_ssl è il parametro corretto per saltare il controllo certificati
            confluence = Confluence(
                url=clean_url,
                token=API_TOKEN,
                verify_ssl=False
            )

        # TEST DI CONNESSIONE: Metodo standard per verificare l'accesso
        # get_all_spaces è il modo più stabile per testare se il token funziona
        print("[INFO] Verifica accesso agli spazi...")
        confluence.get_all_spaces(start=0, limit=1)
        print("[SUCCESS] Connessione stabilita correttamente!")

    except Exception as e:
        print(f"[FATAL] Errore autenticazione: {e}")
        print("\nPossibili cause:")
        print("- Il token non ha permessi di lettura API.")
        print("- La VPN Enel non è attiva o Docker non vi accede.")
        print("- L'URL non è raggiungibile.")
        sys.exit(1)

    output_dir = "/app/downloaded_pages"
    os.makedirs(output_dir, exist_ok=True)

    try:
        if PARENT_PAGE_ID:
            print(f"[MODE] Esportazione dalla pagina ID: {PARENT_PAGE_ID}")
            download_recursive(confluence, PARENT_PAGE_ID, output_dir)
            
        elif SPACE_KEY:
            print(f"[MODE] Esportazione Space: {SPACE_KEY}")
            # Otteniamo le pagine top-level dello space
            # In Data Center, 'get_all_pages_from_space' senza filtri può essere enorme.
            # Meglio iterare sulle pagine che non hanno genitori.
            all_pages = confluence.get_all_pages_from_space(SPACE_KEY, start=0, limit=500)
            
            for page in all_pages:
                # Verifichiamo se è una pagina radice (senza parent)
                parent_id = confluence.get_parent_content_id(page['id'])
                if not parent_id:
                    print(f"Trovata pagina radice: {page['title']}")
                    download_recursive(confluence, page['id'], output_dir)
        else:
            print("[ERROR] Mancano SPACE_KEY o PARENT_PAGE_ID.")
            
    except Exception as e:
        print(f"[FATAL] Errore: {e}")

if __name__ == "__main__":
    # --- DEBUG DELLE VARIABILI (SICURO) ---
    print("--- Verifica Variabili d'Ambiente ---")
    print(f"URL:    {URL}")
    print(f"USER:   {USERNAME if USERNAME else '(Non impostato, uso PAT mode)'}")
    print(f"TOKEN:  {API_TOKEN[:5]}...{API_TOKEN[-5:] if API_TOKEN else 'MANCANTE'}")
    print(f"SPACE:  {SPACE_KEY}")
    print(f"PARENT: {PARENT_PAGE_ID}")
    print("-------------------------------------")
    main()