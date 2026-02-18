"""
AI analyzer for municipal documents using Ollama local models
"""

import requests
import json
import os

def analyze_document_with_ollama(document_text: str, model: str = "mistral", prompt_file: str = None) -> dict:
    """
    Analyze a document using Ollama local AI
    
    Args:
        document_text: The text content to analyze
        model: Ollama model to use (mistral, llama2, tinyllama, etc.)
        prompt_file: Path to prompt file (default: prompt_ia_analyse.md)
    
    Returns:
        dict with ia_pertinent, ia_score, ia_resume, ia_justification
    """
    
    # Load prompt from file
    if prompt_file is None:
        prompt_file = os.path.join(os.path.dirname(__file__), '..', 'prompt_ia_analyse.md')
    
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            system_prompt = f.read()
    except Exception as e:
        print(f"Warning: Could not load prompt file: {e}")
        system_prompt = """Tu es un expert en analyse de documents municipaux français spécialisé dans l'identification de projets liés aux énergies renouvelables et à la transition énergétique.

Analyse le document et retourne un JSON avec:
- ia_pertinent: true/false
- ia_score: 0-10
- ia_resume: résumé concis
- ia_justification: explication détaillée

Recherche particulièrement: biomasse, chaufferies bois, réseaux de chaleur, solaire, PCAET, transition énergétique."""
    
    # Truncate document if too long (keep first 4000 chars for context)
    max_length = 4000
    if len(document_text) > max_length:
        document_text = document_text[:max_length] + "\n\n[...document tronqué...]"
    
    # Build prompt - very strict for TinyLlama
    full_prompt = f"""{system_prompt}

# Document à analyser

{document_text}

# IMPORTANT: Ta réponse doit être UNIQUEMENT un objet JSON valide, RIEN D'AUTRE.
# Ne commence PAS par "Sure!" ou "Voici" ou toute autre phrase.
# Ne mets PAS de backticks ou de markdown.
# Retourne DIRECTEMENT le JSON, première ligne = première accolade.

Format JSON EXACT requis:
{{"ia_pertinent": true, "ia_score": 8, "ia_resume": "résumé court", "ia_justification": "explication"}}

JSON:"""
    
    # Call Ollama API
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                'model': model,
                'prompt': full_prompt,
                'stream': False,
                'options': {
                    'temperature': 0.1,
                    'num_predict': 500
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get('response', '').strip()
            
            # Try to parse JSON from response
            # Remove markdown code blocks if present
            if '```json' in ai_response:
                ai_response = ai_response.split('```json')[1].split('```')[0].strip()
            elif '```' in ai_response:
                ai_response = ai_response.split('```')[1].split('```')[0].strip()
            
            # Parse JSON
            try:
                print(f"[DEBUG] AI raw response: {ai_response[:500]}")
                analysis = json.loads(ai_response)
                
                print(f"[DEBUG] Parsed successfully: pertinent={analysis.get('ia_pertinent')}, score={analysis.get('ia_score')}")
                
                # Validate and return
                return {
                    'ia_pertinent': bool(analysis.get('ia_pertinent', False)),
                    'ia_score': int(analysis.get('ia_score', 0)),
                    'ia_resume': str(analysis.get('ia_resume', '')),
                    'ia_justification': str(analysis.get('ia_justification', ''))
                }
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse AI response as JSON: {e}")
                print(f"[ERROR] Full response was: {ai_response}")
                
                # Fallback: try to extract info from text using regex
                # Look for keywords that indicate relevance
                keywords = ['biomasse', 'chaufferie', 'solaire', 'éolien', 'renouvelable', 'pcaet', 'transition énergétique']
                text_lower = ai_response.lower()
                found_keywords = [kw for kw in keywords if kw in text_lower]
                
                if found_keywords:
                    print(f"[FALLBACK] Found keywords in response: {found_keywords}")
                    return {
                        'ia_pertinent': True,
                        'ia_score': 5,
                        'ia_resume': f'Document mentionnant: {", ".join(found_keywords)}',
                        'ia_justification': f'Réponse IA non-JSON mais contient mots-clés pertinents. Réponse: {ai_response[:200]}'
                    }
                else:
                    return {
                        'ia_pertinent': False,
                        'ia_score': 0,
                        'ia_resume': 'Erreur de parsing JSON',
                        'ia_justification': f'Réponse IA invalide: {ai_response[:100]}'
                    }
        else:
            print(f"Ollama API error: {response.status_code}")
            return {
                'ia_pertinent': False,
                'ia_score': 0,
                'ia_resume': 'Erreur API Ollama',
                'ia_justification': f'HTTP {response.status_code}'
            }
            
    except requests.exceptions.ConnectionError:
        print("Cannot connect to Ollama. Is it running? (ollama serve)")
        return {
            'ia_pertinent': False,
            'ia_score': 0,
            'ia_resume': 'Ollama non disponible',
            'ia_justification': 'Impossible de se connecter à Ollama sur localhost:11434'
        }
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return {
            'ia_pertinent': False,
            'ia_score': 0,
            'ia_resume': 'Erreur analyse IA',
            'ia_justification': str(e)
        }

def check_ollama_available() -> bool:
    """Check if Ollama is running and available"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        return response.status_code == 200
    except:
        return False

def get_available_models() -> list:
    """Get list of available Ollama models"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        return []
    except:
        return []
