import json
import os
import time
import requests
from typing import Dict, List, Optional
from datetime import datetime

# Configuration Ollama
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"  # Mistral-7B Instruct
MAX_RETRIES = 3
TIMEOUT = 90  # secondes - augmenté pour Mistral
BATCH_SIZE = 2  # Petit batch pour M1

# Paramètres d'optimisation Mistral
MODEL_PARAMS = {
    "temperature": 0.1,  # Réponses plus déterministes
    "top_p": 0.9,
    "repeat_penalty": 1.1,
    "num_ctx": 1024,  # Contexte très réduit pour M1
    "num_thread": 4  # Limite threads CPU
}

# Prompt système pour l'analyse - VERSION STRICTE
SYSTEM_PROMPT = """Tu es un expert en analyse de documents administratifs français, spécialisé dans la détection EXCLUSIVE de projets énergétiques collectifs (chaufferie biomasse, réseaux de chaleur, bois énergie).

Ta mission : analyser le texte fourni et détecter UNIQUEMENT les documents réellement pertinents.

DEFINITION DE PERTINENCE (tous les critères doivent être remplis) :
1. Le document décrit UN PROJET CONCRET (étude, marché, délibération, convention, installation)
2. Le projet concerne explicitement : chaufferie biomasse, réseau de chaleur, chaudière bois, chauffage collectif au bois, ou projet énergétique collectif
3. Le document contient PLUS que juste un accusé de réception ou en-tête administratif

DOCUMENTS NON PERTINENTS (score = 0, pertinent = false) :
- Accusés de réception seuls sans contenu substantiel
- Documents mentionnant seulement le mot "énergie" ou "électricité" sans lien avec chaufferie biomasse
- Contrats de maintenance génériques sans spécification biomasse/bois
- Budgets annuels sans projet énergétique spécifique

Réponds UNIQUEMENT au format JSON :
{
    "pertinent": true/false,
    "score": 0-10,
    "resume": "Résumé en 1 phrase",
    "justification": "Pourquoi pertinent/non (20 mots max)"
}"""

def call_ollama(text: str, retries: int = MAX_RETRIES) -> Optional[Dict]:
    """Appel à Ollama avec retries"""
    # Réduit la taille du contexte pour M1
    # Réduit le contexte pour M1
    text_tronque = text[:1000]
    prompt = f"{SYSTEM_PROMPT}\n\nTexte à analyser :\n---\n{text_tronque}\n---\n\nRéponse JSON :"
    
    for attempt in range(retries):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    **MODEL_PARAMS
                },
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                result = response.json()
                # Parse la réponse JSON de l'IA
                try:
                    ia_result = json.loads(result.get('response', '{}'))
                    return {
                        'ia_pertinent': ia_result.get('pertinent', False),
                        'ia_score': ia_result.get('score', 0),
                        'ia_resume': ia_result.get('resume', ''),
                        'ia_justification': ia_result.get('justification', ''),
                        'ia_timestamp': datetime.utcnow().isoformat()
                    }
                except json.JSONDecodeError:
                    print(f"[IA] Erreur parsing JSON, tentative {attempt+1}/{retries}")
                    continue
            else:
                print(f"[IA] HTTP {response.status_code}, tentative {attempt+1}/{retries}")
        except requests.exceptions.Timeout:
            print(f"[IA] Timeout, tentative {attempt+1}/{retries}")
        except Exception as e:
            print(f"[IA] Erreur: {e}, tentative {attempt+1}/{retries}")
        
        if attempt < retries - 1:
            time.sleep(2 ** attempt)  # Backoff exponentiel
    
    return None

def analyze_pdf(pdf_path: str, json_path: str) -> bool:
    """Analyse un PDF avec Ollama et enrichit le JSON"""
    try:
        # Lire le JSON existant
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Vérifier si déjà analysé
        if data.get('ia_analyse') or data.get('ia_pertinent') is not None:
            print(f"Déjà analysé : {pdf_path}")
            return True
        
        # Vérifier qu'il y a du texte
        text = data.get('texte', '').strip()
        if not text or len(text) < 50:
            print(f"Pas de texte suffisant : {pdf_path}")
            return False
        
        # Filtrage préliminaire strict - mots-clés énergie obligatoires
        energy_keywords = [
            'biomasse', 'chauffage', 'biomasse', 'bois', 'chaudière', 'réseau de chaleur', 
            'solaire', 'photovoltaïque', 'éolien', 'géothermie', 'hydrogène', 'biogaz',
            'autoconsommation', 'rénovation énergétique', 'isolation', 'bbc'
        ]
        
        text_lower = text.lower()
        has_energy_keyword = any(keyword in text_lower for keyword in energy_keywords)
        
        if not has_energy_keyword:
            print(f"Pas de mot-clé énergie : {pdf_path}")
            # Marquer comme non pertinent pour éviter réanalyse
            data['ia_pertinent'] = False
            data['ia_score'] = 0
            data['ia_resume'] = 'Document non pertinent (pas de mot-clé énergie)'
            data['ia_justification'] = 'Aucun terme énergie détecté'
            data['ia_timestamp'] = datetime.now().isoformat()
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        
        # Appel à Ollama
        result = call_ollama(text)
        if result:
            # Parser la réponse JSON
            try:
                ia_result = json.loads(result)
                score = ia_result.get('score', 0)
                
                # Normaliser le score : si >10, le diviser par 10
                if score > 10:
                    score = score / 10
                
                # Validation stricte du score
                if not isinstance(score, (int, float)) or score < 0 or score > 10:
                    score = 0
                
                # Seuils plus stricts
                ia_pertinent = ia_result.get('pertinent', False) and score >= 7
                
                # Correction automatique si incohérence
                if ia_pertinent and score < 7:
                    ia_pertinent = False
                    ia_result['justification'] = f"Score trop bas ({score}/10)"
                elif not ia_pertinent and score >= 7:
                    score = 3  # Baisser le score si non pertinent
                
                data.update({
                    'ia_pertinent': ia_pertinent,
                    'ia_score': score,
                    'ia_resume': ia_result.get('resume', ''),
                    'ia_justification': ia_result.get('justification', ''),
                    'ia_timestamp': datetime.now().isoformat()
                })
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"✅ Analysé : {pdf_path} -> pertinent={ia_pertinent}, score={score}/10")
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ Erreur parsing JSON {pdf_path}: {e}")
                return False
        
        return False
        
    except Exception as e:
        print(f"❌ Erreur analyse {pdf_path}: {e}")
        return False

def batch_analyze(base_dir: str = 'data/pdf_texts'):
    """Analyse batch de tous les PDF éligibles"""
    # Collecte des fichiers
    json_files = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.json') and file != 'index_global.json':
                json_files.append(os.path.join(root, file))
    
    print(f"[BATCH] {len(json_files)} fichiers trouvés")
    
    # Filtrer les éligibles (non analysés, statut correct)
    eligible = []
    for path in json_files:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if (data.get('statut') in ['texte', 'ocr_ok'] and 
                data.get('texte', '').strip() and
                'ia_pertinent' not in data):
                eligible.append(path)
        except:
            continue
    
    print(f"[BATCH] {len(eligible)} PDF éligibles pour analyse IA")
    
    # Traitement par lots
    analyzed = 0
    for i, path in enumerate(eligible, 1):
        if analyze_pdf(path):
            analyzed += 1
        
        # Pause entre lots
        if i % BATCH_SIZE == 0:
            print(f"[BATCH] Pause... ({i}/{len(eligible)} traités)")
            time.sleep(2)
    
    print(f"[BATCH] Terminé: {analyzed}/{len(eligible)} analysés avec succès")
    
    # Générer index global
    build_ia_index(base_dir)

def build_ia_index(base_dir: str):
    """Génère un index global des analyses IA"""
    index = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.json') and file != 'index_global.json':
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Ne garder que les analyses IA
                    if 'ia_pertinent' in data:
                        index.append({
                            'fichier': data.get('nom_fichier'),
                            'site': data.get('site_url'),
                            'statut_pdf': data.get('statut'),
                            'ia_pertinent': data.get('ia_pertinent'),
                            'ia_score': data.get('ia_score'),
                            'ia_resume': data.get('ia_resume'),
                            'json_path': path
                        })
                except:
                    continue
    
    # Sauvegarder index
    index_path = os.path.join(base_dir, 'index_ia_global.json')
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump({
            'total_analyses': len(index),
            'pertinents': sum(1 for x in index if x['ia_pertinent']),
            'analyses': sorted(index, key=lambda x: x['ia_score'], reverse=True)
        }, f, ensure_ascii=False, indent=2)
    
    print(f"[INDEX] {len(index)} analyses sauvegardées dans {index_path}")

if __name__ == "__main__":
    batch_analyze()
