import os
import sys
import urllib3
import requests
from atlassian import Confluence
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Disabilita i warning SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURAZIONE ---
def get_env_var(name, default=None):
    val = os.getenv(name, default)
    if val is None or str(val).lower() in ("none", ""):
        return None
    return str(val).strip()

URL = get_env_var("CONFLUENCE_URL")
if URL: URL = URL.rstrip('/')

USERNAME = get_env_var("CONFLUENCE_USER")
API_TOKEN = get_env_var("CONFLUENCE_TOKEN")
SPACE_KEY = get_env_var("SPACE_KEY")
PARENT_PAGE_ID = get_env_var("PARENT_PAGE_ID")

def clean_filename(title):
    return "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()

def download_attachments(confluence, page_id, target_dir):
    """Scarica le immagini della pagina e restituisce una mappa per il re-linking."""
    img_mapping = {}
    try:
        attachments = confluence.get_attachments_from_content(page_id, start=0, limit=50)
        if attachments['results']:
            img_dir = os.path.join(target_dir, "attachments")
            os.makedirs(img_dir, exist_ok=True)
            
            for attach in attachments['results']:
                file_name = attach['title']
                # Filtriamo solo file immagine per il RAG
                if any(file_name.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg']):
                    download_url = confluence.url + attach['_links']['download']
                    res = confluence.session.get(download_url, stream=True, verify=False)
                    if res.status_code == 200:
                        file_path = os.path.join(img_dir, file_name)
                        with open(file_path, 'wb') as f:
                            for chunk in res.iter_content(8192): f.write(chunk)
                        # Percorso relativo per il Markdown
                        img_mapping[file_name] = f"./attachments/{file_name}"
    except Exception as e:
        print(f"  [WARN] Impossibile scaricare allegati per {page_id}: {e}")
    return img_mapping

def html_to_rag_markdown(html_content, title, page_id, img_mapping):
    """Converte HTML in MD preservando tabelle HTML e link immagini locali."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Pulizia: Rimuoviamo macro di sistema o elementi UI
    for el in soup(['script', 'style', 'nav', 'header', 'footer']): el.decompose()

    # 2. Re-linking Immagini: Sostituiamo i nodi img di Confluence con i file locali
    for img in soup.find_all('img'):
        # Confluence usa spesso 'data-linked-resource-default-alias' per il nome file
        orig_name = img.get('data-linked-resource-default-alias') or img.get('title')
        if orig_name in img_mapping:
            img['src'] = img_mapping[orig_name]

    # 3. Conversione: manteniamo le tabelle in HTML (fondamentale per RAG)
    markdown_text = md(
        str(soup),
        heading_style="ATX",
        bullets="-",
        convert=['table', 'tr', 'td', 'th', 'b', 'i', 'strong', 'em']
    )
    
    # Header YAML per metadati RAG
    header = f"---\ntitle: {title}\npage_id: {page_id}\nsource: {URL}/pages/viewpage.action?pageId={page_id}\n---\n\n"
    return header + f"# {title}\n\n{markdown_text}"

def download_recursive(confluence, page_id, path, level=0):
    try:
        page = confluence.get_page_by_id(page_id, expand='body.storage')
        title = clean_filename(page['title'])
        html_raw = page['body']['storage']['value']
        
        # Percorso cartella per questa pagina
        current_page_dir = os.path.join(path, title)
        os.makedirs(current_page_dir, exist_ok=True)
        
        # Scarichiamo immagini e creiamo MD
        img_map = download_attachments(confluence, page_id, current_page_dir)
        content_md = html_to_rag_markdown(html_raw, page['title'], page_id, img_map)
        
        with open(os.path.join(current_page_dir, "index.md"), "w", encoding="utf-8") as f:
            f.write(content_md)
            
        print(f"{'  ' * level}✔ {title} (MD + {len(img_map)} immagini)")
        
        # Ricorsione
        children = confluence.get_page_child_by_type(page_id, type='page')
        for child in children:
            download_recursive(confluence, child['id'], current_page_dir, level + 1)
            
    except Exception as e:
        print(f"[WARN] Errore sulla pagina {page_id}: {e}")

def main():
    if not URL or not API_TOKEN:
        print("[ERROR] Variabili mancanti."); sys.exit(1)

    try:
        if USERNAME:
            confluence = Confluence(url=URL, username=USERNAME, password=API_TOKEN, cloud=True, verify_ssl=False)
        else:
            confluence = Confluence(url=URL, token=API_TOKEN, verify_ssl=False)
        
        # Forza lingua italiana per evitare traduzioni automatiche
        # confluence.session.headers.update({'Accept-Language': 'it-IT,it;q=0.9'})
        confluence.get_all_spaces(start=0, limit=1)
        print("[SUCCESS] Connessione stabilita!")

    except Exception as e:
        print(f"[FATAL] Autenticazione fallita: {e}"); sys.exit(1)

    output_root = get_env_var("OUTPUT_DIR") or "./output"
    os.makedirs(output_root, exist_ok=True)

    if PARENT_PAGE_ID:
        download_recursive(confluence, PARENT_PAGE_ID, output_root)
    elif SPACE_KEY:
        all_pages = confluence.get_all_pages_from_space(SPACE_KEY, start=0, limit=500)
        for p in all_pages:
            if not confluence.get_parent_content_id(p['id']):
                download_recursive(confluence, p['id'], output_root)

if __name__ == "__main__":
    main()