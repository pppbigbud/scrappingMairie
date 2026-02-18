import os
import json
import asyncio
from pdf_pipeline.process import batch_process_pdfs

# Point d'entrée du pipeline PDF
# Consomme les exports JSON du crawler dans data/crawl_results/
# Génère un fichier JSON par PDF traité dans data/pdf_texts/<site>/
# Génère un index global récapitulatif

CRAWL_RESULTS_DIR = os.path.join('data', 'crawl_results')
PDF_TEXTS_DIR = os.path.join('data', 'pdf_texts')

# Récupère toutes les métadonnées PDF à traiter à partir des exports de crawl
def collect_pdf_metas():
    metas = []
    for fname in os.listdir(CRAWL_RESULTS_DIR):
        if fname.endswith('.json'):
            fpath = os.path.join(CRAWL_RESULTS_DIR, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for meta in data:
                        if meta.get('type') == 'pdf':
                            metas.append(meta)
            except Exception as e:
                print(f"[COLLECT] Erreur lecture {fpath} : {e}")
    return metas

async def main():
    metas = collect_pdf_metas()
    print(f"[MAIN] {len(metas)} PDF à traiter.")
    await batch_process_pdfs(metas, PDF_TEXTS_DIR)
    print("[MAIN] Traitement terminé. Lancement index global...")
    from pdf_pipeline.index import build_global_index
    build_global_index(PDF_TEXTS_DIR)

if __name__ == "__main__":
    asyncio.run(main())
