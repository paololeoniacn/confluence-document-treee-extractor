import os
import sys
import urllib3
from atlassian import Confluence
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Disabilita i warning SSL per rete interna
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. CONFIGURAZIONE ---
def get_env_var(name, default=None):
    val = os.getenv(name, default)
    if val is None or str(val).lower() in ("none", ""):
        return None
    return str(val).strip()

URL = get_env_var("CONFLUENCE_URL")
if URL:
    URL = URL.rstrip('/')

USERNAME = get_env_var("CONFLUENCE_USER")
API_TOKEN = get_env_var("CONFLUENCE_TOKEN")
SPACE_KEY = get_env_var("SPACE_KEY")
PARENT_PAGE_ID = get_env_var("PARENT_PAGE_ID")

def clean_filename(title):
    """Rimuove caratteri non validi per i nomi dei file."""
    return "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()

def html_to_markdown(html_content, title, page_id):
    """Pulisce l'HTML e lo converte in Markdown ottimizzato per RAG."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Rimuoviamo elementi inutili che sporcano il RAG
    for tag in soup(['script', 'style', 'noscript', 'nav']):
        tag.decompose()

    clean_html = str(soup)
    
    # Conversione in Markdown
    # heading_style="ATX" usa i '#' per i titoli (più leggibile dai chunker)
    markdown_text = md(
        clean_html, 
        heading_style="ATX", 
        bullets="-",
        strip=['img', 'a'] # Opzionale: rimuovi immagini e link se non servono al RAG
    )
    
    # Aggiungiamo un header di metadati in formato YAML-like (utile per i LLM)
    header = f"---\ntitle: {title}\npage_id: {page_id}\n---\n\n"
    return header + f"# {title}\n\n{markdown_text}"

def download_recursive(confluence, page_id, path, level=0):
    try:
        # Recuperiamo la pagina
        page = confluence.get_page_by_id(page_id, expand='body.storage')
        title = clean_filename(page['title'])
        html_raw = page['body']['storage']['value']
        
        # Conversione
        content_md = html_to_markdown(html_raw, page['title'], page_id)
        
        # Salvataggio: usiamo il titolo per il file
        file_name = f"{title}.md"
        file_path = os.path.join(path, file_name)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content_md)
            
        print(f"{'  ' * level}✔ Salvato MD: {file_name}")
        
        # Ricorsione sui figli (mantenendo la struttura a cartelle)
        children = confluence.get_page_child_by_type(page_id, type='page')
        for child in children:
            # Creiamo una sottocartella per i figli
            child_dir = os.path.join(path, title)
            os.makedirs(child_dir, exist_ok=True)
            download_recursive(confluence, child['id'], child_dir, level + 1)
            
    except Exception as e:
        print(f"[WARN] Errore sulla pagina {page_id}: {e}")

def main():
    if not URL or not API_TOKEN:
        print("[ERROR] URL o TOKEN mancanti.")
        sys.exit(1)

    try:
        # Autenticazione
        if USERNAME:
            print(f"[AUTH] Modalità Basic per: {USERNAME}")
            confluence = Confluence(url=URL, username=USERNAME, password=API_TOKEN, cloud=True, verify_ssl=False)
        else:
            print("[AUTH] Modalità PAT (Bearer)")
            confluence = Confluence(url=URL, token=API_TOKEN, verify_ssl=False)

        # Test connessione
        confluence.get_all_spaces(start=0, limit=1)
        print("[SUCCESS] Connessione OK!")

    except Exception as e:
        print(f"[FATAL] Errore connessione: {e}")
        sys.exit(1)

    # Allineamento con cartella Docker
    output_dir = "/app/downloaded_pages"
    os.makedirs(output_dir, exist_ok=True)

    try:
        if PARENT_PAGE_ID:
            print(f"[MODE] Esportazione Ricorsiva da ID: {PARENT_PAGE_ID}")
            download_recursive(confluence, PARENT_PAGE_ID, output_dir)
        elif SPACE_KEY:
            print(f"[MODE] Esportazione Space: {SPACE_KEY}")
            all_pages = confluence.get_all_pages_from_space(SPACE_KEY, start=0, limit=500)
            for page in all_pages:
                if not confluence.get_parent_content_id(page['id']):
                    download_recursive(confluence, page['id'], output_dir)
    except Exception as e:
        print(f"[FATAL] Errore durante l'esportazione: {e}")

if __name__ == "__main__":
    main()