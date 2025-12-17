import os
import sys
from atlassian import Confluence
from markdownify import markdownify as md

# Caricamento variabili d'ambiente
URL = os.getenv("CONFLUENCE_URL")
USERNAME = os.getenv("CONFLUENCE_USER")
API_TOKEN = os.getenv("CONFLUENCE_TOKEN")
PARENT_PAGE_ID = os.getenv("PARENT_PAGE_ID")

def test_connection(confluence):
    try:
        confluence.get_all_spaces(limit=1)
        print(f"[SUCCESS] Connessione a Confluence riuscita.")
        return True
    except Exception as e:
        print(f"[ERROR] Autenticazione fallita: {e}")
        return False

def check_root_page(confluence, page_id):
    try:
        page = confluence.get_page_by_id(page_id)
        print(f"[SUCCESS] Pagina radice trovata: '{page['title']}'")
        return True
    except Exception as e:
        print(f"[ERROR] Impossibile trovare la pagina {page_id}: {e}")
        return False

def main():
    if not all([URL, USERNAME, API_TOKEN, PARENT_PAGE_ID]):
        print("[ERROR] Variabili d'ambiente mancanti.")
        sys.exit(1)

    confluence = Confluence(url=URL, username=USERNAME, password=API_TOKEN, cloud=True)

    print("--- Avvio Test di Connettività ---")
    if not test_connection(confluence) or not check_root_page(confluence, PARENT_PAGE_ID):
        sys.exit(1)
    print("--- Test completati con successo ---\n")

    output_dir = "downloaded_pages"
    os.makedirs(output_dir, exist_ok=True)

    def download_recursive(page_id, path, level=0):
        try:
            page = confluence.get_page_by_id(page_id, expand='body.storage')
            title = page['title'].replace("/", "-").replace("\\", "-")
            html_content = page['body']['storage']['value']
            
            # Conversione da HTML a Markdown
            # 'heading_style' e 'bullets' rendono l'output più standard
            md_content = md(html_content, heading_style="ATX", bullets="-")
            
            current_path = os.path.join(path, title)
            os.makedirs(current_path, exist_ok=True)
            
            # Salvataggio in formato .md
            file_path = os.path.join(current_path, f"{title}.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# {page['title']}\n\n")
                f.write(md_content)
            
            indent = "  " * level
            print(f"{indent}Scaricato (MD): {title}")
            
            # Ricorsione sui figli
            children = confluence.get_page_child_by_type(page_id, type='page')
            for child in children:
                download_recursive(child['id'], current_path, level + 1)
                
        except Exception as e:
            print(f"[WARN] Errore sulla pagina {page_id}: {e}")

    print(f"Inizio download ricorsivo in formato Markdown...")
    download_recursive(PARENT_PAGE_ID, output_dir)
    print("\n[FINISH] Operazione completata!")

if __name__ == "__main__":
    main()