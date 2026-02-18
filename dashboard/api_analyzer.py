"""
External API analyzer for municipal documents using Groq, OpenRouter, Together.ai, or OpenAI
"""

import requests
import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional

def load_prompt():
    """Load the analysis prompt from file"""
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompt_ia_analyse.md')
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """Analyse ce document municipal et identifie les projets d'énergies renouvelables.
Recherche: biomasse, chaufferies bois, réseaux de chaleur, solaire, PCAET, transition énergétique."""

def analyze_document_with_api(
    document_text: str,
    api_provider: str = 'groq',
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze a document using external API
    
    Args:
        document_text: Text content to analyze
        api_provider: 'groq', 'openrouter', 'together', or 'openai'
        api_key: API key for the provider
        model: Model name (optional, uses default for provider)
    
    Returns:
        Dictionary with ia_pertinent, ia_score, ia_resume, ia_justification
    """
    
    # Default result
    default_result = {
        'ia_pertinent': False,
        'ia_score': 0,
        'ia_resume': 'Erreur API',
        'ia_justification': 'Impossible de contacter l\'API',
        'ia_timestamp': datetime.now().isoformat()
    }
    
    if not api_key:
        default_result['ia_justification'] = 'Clé API manquante'
        return default_result
    
    # Load system prompt
    system_prompt = load_prompt()
    
    # Truncate document if too long
    max_length = 8000
    if len(document_text) > max_length:
        document_text = document_text[:max_length] + "\n\n[...document tronqué...]"
    
    # Build prompt
    full_prompt = f"""{system_prompt}

# Document à analyser

{document_text}

# IMPORTANT: Réponds UNIQUEMENT avec un objet JSON valide, sans markdown, sans backticks.
# Format JSON EXACT requis:
{{"ia_pertinent": true, "ia_score": 8, "ia_resume": "résumé court", "ia_justification": "explication"}}

JSON:"""
    
    # Configure API endpoint and headers based on provider
    if api_provider == 'groq':
        url = 'https://api.groq.com/openai/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        default_model = model or 'llama-3.1-8b-instant'
        payload = {
            'model': default_model,
            'messages': [
                {'role': 'system', 'content': 'Tu es un expert en analyse de documents municipaux. Réponds UNIQUEMENT en JSON valide.'},
                {'role': 'user', 'content': full_prompt}
            ],
            'temperature': 0.1,
            'max_tokens': 500
        }
        
    elif api_provider == 'openrouter':
        url = 'https://openrouter.ai/api/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://github.com/openclaw',
            'X-Title': 'OpenClaw Municipal Scraper'
        }
        default_model = model or 'meta-llama/llama-3.1-8b-instruct'
        payload = {
            'model': default_model,
            'messages': [
                {'role': 'system', 'content': 'Tu es un expert en analyse de documents municipaux. Réponds UNIQUEMENT en JSON valide.'},
                {'role': 'user', 'content': full_prompt}
            ],
            'temperature': 0.1,
            'max_tokens': 500
        }
        
    elif api_provider == 'together':
        url = 'https://api.together.xyz/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        default_model = model or 'meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo'
        payload = {
            'model': default_model,
            'messages': [
                {'role': 'system', 'content': 'Tu es un expert en analyse de documents municipaux. Réponds UNIQUEMENT en JSON valide.'},
                {'role': 'user', 'content': full_prompt}
            ],
            'temperature': 0.1,
            'max_tokens': 500
        }
        
    elif api_provider == 'openai':
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        default_model = model or 'gpt-4o-mini'
        payload = {
            'model': default_model,
            'messages': [
                {'role': 'system', 'content': 'Tu es un expert en analyse de documents municipaux. Réponds UNIQUEMENT en JSON valide.'},
                {'role': 'user', 'content': full_prompt}
            ],
            'temperature': 0.1,
            'max_tokens': 500
        }
    else:
        default_result['ia_justification'] = f'Provider inconnu: {api_provider}'
        return default_result
    
    # Call API with retry logic for rate limiting
    max_retries = 5
    retry_delay = 5  # Start with 5 seconds for better rate limit handling
    
    for attempt in range(max_retries):
        try:
            print(f"[API] Calling {api_provider} with model {default_model}... (attempt {attempt + 1}/{max_retries})")
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            # Handle rate limiting (429)
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    # Use retry-after header if available, otherwise exponential backoff
                    retry_after = response.headers.get('retry-after')
                    if retry_after:
                        wait_time = int(retry_after)
                        print(f"[API] Rate limit hit (429). Groq says to wait {wait_time}s (from retry-after header)...")
                    else:
                        wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                        print(f"[API] Rate limit hit (429). Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"[API] Rate limit hit after {max_retries} attempts. Giving up.")
                    default_result['ia_justification'] = f'Rate limit dépassé après {max_retries} tentatives. Réessayez dans quelques minutes.'
                    return default_result
            
            response.raise_for_status()
            result = response.json()
            break  # Success, exit retry loop
            
        except requests.exceptions.HTTPError as e:
            if attempt < max_retries - 1 and '429' in str(e):
                wait_time = retry_delay * (2 ** attempt)
                print(f"[API] Rate limit error. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            else:
                raise  # Re-raise if not rate limit or last attempt
    else:
        # This shouldn't happen but just in case
        default_result['ia_justification'] = 'Erreur inattendue lors des tentatives API'
        return default_result
    
    try:
        
        # Extract response text
        if 'choices' in result and len(result['choices']) > 0:
            response_text = result['choices'][0]['message']['content'].strip()
            print(f"[API] Response: {response_text[:200]}...")
            
            # Try to parse JSON
            try:
                # Remove markdown code blocks if present
                if response_text.startswith('```'):
                    response_text = response_text.split('```')[1]
                    if response_text.startswith('json'):
                        response_text = response_text[4:]
                    response_text = response_text.strip()
                
                parsed = json.loads(response_text)
                
                return {
                    'ia_pertinent': bool(parsed.get('ia_pertinent', False)),
                    'ia_score': int(parsed.get('ia_score', 0)),
                    'ia_resume': str(parsed.get('ia_resume', '')),
                    'ia_justification': str(parsed.get('ia_justification', '')),
                    'ia_timestamp': datetime.now().isoformat()
                }
                
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse JSON: {e}")
                print(f"[ERROR] Response was: {response_text}")
                
                # Fallback: keyword detection
                keywords = ['biomasse', 'chaufferie', 'solaire', 'photovoltaïque', 'éolien', 
                           'géothermie', 'méthanisation', 'pcaet', 'transition énergétique',
                           'réseau de chaleur', 'énergies renouvelables']
                
                found_keywords = [kw for kw in keywords if kw.lower() in response_text.lower()]
                
                if found_keywords:
                    print(f"[FALLBACK] Found keywords in response: {found_keywords}")
                    return {
                        'ia_pertinent': True,
                        'ia_score': 5,
                        'ia_resume': f"Document mentionnant: {', '.join(found_keywords[:3])}",
                        'ia_justification': f"Réponse API non-JSON mais contient mots-clés pertinents. Réponse: {response_text[:200]}",
                        'ia_timestamp': datetime.now().isoformat()
                    }
                
                return {
                    'ia_pertinent': False,
                    'ia_score': 0,
                    'ia_resume': 'Erreur de parsing JSON',
                    'ia_justification': f'Réponse API invalide: {response_text[:200]}',
                    'ia_timestamp': datetime.now().isoformat()
                }
        else:
            print(f"[ERROR] Unexpected API response format: {result}")
            default_result['ia_justification'] = 'Format de réponse API inattendu'
            return default_result
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] API request failed: {e}")
        default_result['ia_justification'] = f'Erreur API: {str(e)[:100]}'
        return default_result
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        default_result['ia_justification'] = f'Erreur inattendue: {str(e)[:100]}'
        return default_result
