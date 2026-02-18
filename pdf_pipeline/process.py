import os
import json
import asyncio
from datetime import datetime
from pdf_pipeline.download import download_pdf
from pdf_pipeline.pdf_type import detect_pdf_type
from pdf_pipeline.extract_text import extract_pdf_text
from pdf_pipeline.ocr import ocr_pdf

# Traite un PDF à partir des métadonnées du crawler
async def process_pdf(meta, base_outdir):
    result = {
        'source_url': meta['document_url'],
        'site_url': meta['site_url'],
        'nom_fichier': meta['nom_fichier'],
        'date_detection': meta['date_detection'],
        'statut': None,
        'texte': "",
        'erreur': None
    }
    site = meta['site_url'].replace('https://', '').replace('http://', '').replace('/', '_')
    pdf_outdir = os.path.join(base_outdir, site)
    local_path = await download_pdf(meta['document_url'], pdf_outdir)
    if not local_path:
        result['statut'] = 'download_failed'
        result['erreur'] = 'Téléchargement impossible'
    else:
        pdf_type = detect_pdf_type(local_path)
        result['statut'] = pdf_type
        if pdf_type == 'texte':
            result['texte'] = extract_pdf_text(local_path)
        elif pdf_type == 'scanne':
            try:
                ocr_result = ocr_pdf(local_path)
                if ocr_result.strip():
                    result['texte'] = ocr_result
                    result['statut'] = 'ocr_ok'
                else:
                    result['statut'] = 'ocr_failed'
                    result['erreur'] = 'OCR vide ou non concluant'
            except Exception as e:
                result['statut'] = 'ocr_failed'
                result['erreur'] = f'OCR error: {e}'
        elif pdf_type in ('vide', 'protégé', 'corrompu'):
            result['texte'] = ""
    # Sauvegarde individuelle
    save_dir = os.path.join(base_outdir, site)
    os.makedirs(save_dir, exist_ok=True)
    out_path = os.path.join(save_dir, meta['nom_fichier'] + '.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[PDF] Résultat sauvegardé : {out_path}")
    return result

# Batch sur liste de métadonnées
async def batch_process_pdfs(metas, base_outdir):
    results = []
    for meta in metas:
        res = await process_pdf(meta, base_outdir)
        results.append(res)
    return results
