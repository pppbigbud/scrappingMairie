#!/usr/bin/env python3
"""
TEST RAPIDE - Un seul site pour validation
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

# Test sur Aurillac (confirmé accessible)
url = "https://www.aurillac.fr"
mots_cles = ['chaufferie', 'biomasse', 'chaudière bois', 'bois énergie', 'chauffage collectif']

print(f"🔍 Test rapide: {url}")

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    print(f"📊 Status: {response.status_code}")
    
    if response.status_code == 200:
        print(f"✅ Contenu reçu: {len(response.text)} caractères")
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        texte = soup.get_text().lower()
        
        # Chercher mots-clés
        mots_trouves = []
        for mot in mots_cles:
            if mot.lower() in texte:
                mots_trouves.append(mot)
        
        if mots_trouves:
            print(f"🎯 TROUVÉ: {', '.join(mots_trouves)}")
        else:
            print("⚪ Aucun mot-clé détecté")
            
        # Chercher liens
        liens = soup.find_all('a', href=True)
        print(f"🔗 {len(liens)} liens trouvés")
        
        # Liens intéressants
        liens_interessants = []
        for lien in liens[:20]:
            text = lien.get_text(strip=True).lower()
            if any(mot in text for mot in ['actualité', 'délibération', 'conseil', 'info']):
                liens_interessants.append(lien.get_text(strip=True))
                
        if liens_interessants:
            print(f"📋 Liens intéressants: {liens_interessants[:5]}")
        
    else:
        print(f"❌ Erreur HTTP: {response.status_code}")
        
except Exception as e:
    print(f"💥 Erreur: {e}")

print("\n" + "="*50)
print("✅ Test rapide terminé")