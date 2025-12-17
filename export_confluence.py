import os
import sys
from atlassian import Confluence
from xhtml2pdf import pisa

# Caricamento variabili d'ambiente
URL = os.getenv("CONFLUENCE_URL")
USERNAME = os.getenv("CONFLUENCE_USER")
API_TOKEN = os.getenv("CONFLUENCE_TOKEN")
PARENT_PAGE_ID = os.getenv("PARENT_PAGE_ID")

def convert_html_to_pdf(source_html, output_filename):
    """Converte una stringa HTML in un file PDF."""
    with open(output_filename, "w+b") as result_file:
        # pisa.CreatePDF trasforma l'HTML in PDF
        pisa_status = pisa.CreatePDF(source_html, dest=result_file)
    return not pisa_status.err

def main():
    if not all([URL, USERNAME, API_TOKEN, PARENT_PAGE_ID]):
        print("[ERROR] Variabili d'ambiente mancanti.")
        sys.exit(1)

    confluence = Confluence(url=URL, username=USERNAME, password=API_TOKEN, cloud=True)

    # Test iniziale
    try:
        confluence.get_all_spaces(limit=1)
        print("[SUCCESS] Connessione riuscita.")
    except Exception as e:
        print(f"[ERROR] Errore connessione: {e}")
        sys.exit(1)

    output_dir = "downloaded_pages"
    os.makedirs(output_dir, exist_ok=True)

    def download_recursive(page_id, path, level=0):
        try:
            page = confluence.get_page_by_id(page_id, expand='body.storage')
            title = page['title'].replace("/", "-").replace("\\", "-")
            html_raw = page['body']['storage']['value']
            
            # Prepariamo un HTML minimo con encoding corretto per il PDF
            full_html = f"""
            <html>
            <head><meta charset="UTF-8"></head>
            <body>
                <h1 style="color: #0052cc;">{page['title']}</h1>
                <hr>
                {html_raw}
            </body>
            </html>
            """
            
            current_path = os.path.join(path, title)
            os.makedirs(current_path, exist_ok=True)
            
            # Nome del file PDF
            pdf_path = os.path.join(current_path, f"{title}.pdf")
            
            if convert_html_to_pdf(full_html, pdf_path):
                indent = "  " * level
                print(f"{indent}Creato PDF: {title}.pdf")
            else:
                print(f"Errore nella generazione PDF per: {title}")
            
            # Ricorsione sui figli
            children = confluence.get_page_child_by_type(page_id, type='page')
            for child in children:
                download_recursive(child['id'], current_path, level + 1)
                
        except Exception as e:
            print(f"[WARN] Errore sulla pagina {page_id}: {e}")

    print(f"Inizio esportazione ricorsiva in PDF...")
    download_recursive(PARENT_PAGE_ID, output_dir)
    print("\n[FINISH] Esportazione completata!")

if __name__ == "__main__":
    main()