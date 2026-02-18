#!/usr/bin/env python3
"""
SCRAPER SUITE - Départements restants (42, 43, 63, 69, 73, 74)
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
import time
import random
from urllib.parse import urljoin
import sys

sys.stdout.reconfigure(line_buffering=True)

@dataclass
class Projet:
    commune: str
    dept: str
    mots_cles: List[str]
    url: str
    extrait: str
    contact: Optional[str] = None
    pop: int = 0

MOTS_CLES = [
    'chaufferie', 'chaudière', 'biomasse', 'bois énergie', 'bois-énergie',
    'granulés', 'plaquettes', 'pellets', 'fioul', 'fuel',
    'réseau de chaleur', 'réseau chaleur', 'chauffage collectif',
    'géothermie', 'pompe à chaleur', 'PAC'
]

CONTEXTE = ['projet', 'étude', 'remplacement', 'modernisation', 'rénovation', 'subvention', 'mandat', 'plan climat']

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
]

# Départements restants uniquement
COMMUNES = [
    # === LOIRE (42) ===
    {'commune': 'Saint-Étienne', 'dept': '42', 'url': 'https://www.saint-etienne.fr', 'pop': 174000},
    {'commune': 'Roanne', 'dept': '42', 'url': 'https://www.roanne.fr', 'pop': 35000},
    {'commune': 'Saint-Chamond', 'dept': '42', 'url': 'https://www.saint-chamond.fr', 'pop': 35000},
    {'commune': 'Firminy', 'dept': '42', 'url': 'https://www.ville-firminy.fr', 'pop': 17500},
    {'commune': 'Montbrison', 'dept': '42', 'url': 'https://www.ville-montbrison.fr', 'pop': 16000},
    {'commune': 'Rive-de-Gier', 'dept': '42', 'url': 'https://www.rive-de-gier.fr', 'pop': 16000},
    {'commune': 'Andrézieux-Bouthéon', 'dept': '42', 'url': 'https://www.andrezieux-boutheon.fr', 'pop': 9800},
    {'commune': 'Riorges', 'dept': '42', 'url': 'https://www.riorges.fr', 'pop': 10800},
    {'commune': 'Feurs', 'dept': '42', 'url': 'https://www.feurs.fr', 'pop': 8000},
    
    # === HAUTE-LOIRE (43) ===
    {'commune': 'Le Puy-en-Velay', 'dept': '43', 'url': 'https://www.lepuyenvelay.fr', 'pop': 18700},
    {'commune': 'Monistrol-sur-Loire', 'dept': '43', 'url': 'https://www.monistrol-sur-loire.fr', 'pop': 9000},
    {'commune': 'Yssingeaux', 'dept': '43', 'url': 'https://www.yssingeaux.fr', 'pop': 7200},
    {'commune': 'Brioude', 'dept': '43', 'url': 'https://www.brioude.fr', 'pop': 6700},
    
    # === PUY-DE-DÔME (63) ===
    {'commune': 'Clermont-Ferrand', 'dept': '63', 'url': 'https://www.clermontferrand.fr', 'pop': 147000},
    {'commune': 'Cournon-d\'Auvergne', 'dept': '63', 'url': 'https://www.cournon-auvergne.fr', 'pop': 20000},
    {'commune': 'Riom', 'dept': '63', 'url': 'https://www.ville-riom.fr', 'pop': 19000},
    {'commune': 'Chamalières', 'dept': '63', 'url': 'https://www.ville-chamalieres.fr', 'pop': 17700},
    {'commune': 'Issoire', 'dept': '63', 'url': 'https://www.issoire.fr', 'pop': 14000},
    {'commune': 'Thiers', 'dept': '63', 'url': 'https://www.ville-thiers.fr', 'pop': 11800},
    {'commune': 'Beaumont', 'dept': '63', 'url': 'https://www.beaumont63.fr', 'pop': 11400},
    {'commune': 'Aubière', 'dept': '63', 'url': 'https://www.aubiere.fr', 'pop': 10400},
    {'commune': 'Pont-du-Château', 'dept': '63', 'url': 'https://www.pontduchateau.fr', 'pop': 11500},
    {'commune': 'Lempdes', 'dept': '63', 'url': 'https://www.ville-lempdes.fr', 'pop': 9000},
    
    # === RHÔNE (69) ===
    {'commune': 'Lyon', 'dept': '69', 'url': 'https://www.lyon.fr', 'pop': 522000},
    {'commune': 'Villeurbanne', 'dept': '69', 'url': 'https://www.villeurbanne.fr', 'pop': 152000},
    {'commune': 'Vénissieux', 'dept': '69', 'url': 'https://www.venissieux.fr', 'pop': 66000},
    {'commune': 'Saint-Priest', 'dept': '69', 'url': 'https://www.saint-priest.fr', 'pop': 47000},
    {'commune': 'Caluire-et-Cuire', 'dept': '69', 'url': 'https://www.caluire-et-cuire.fr', 'pop': 43000},
    {'commune': 'Bron', 'dept': '69', 'url': 'https://www.ville-bron.fr', 'pop': 42000},
    {'commune': 'Vaulx-en-Velin', 'dept': '69', 'url': 'https://www.vaulx-en-velin.net', 'pop': 52000},
    {'commune': 'Meyzieu', 'dept': '69', 'url': 'https://www.meyzieu.fr', 'pop': 34000},
    {'commune': 'Rillieux-la-Pape', 'dept': '69', 'url': 'https://www.rillieux-la-pape.fr', 'pop': 31000},
    {'commune': 'Décines-Charpieu', 'dept': '69', 'url': 'https://www.decines.fr', 'pop': 28000},
    {'commune': 'Oullins', 'dept': '69', 'url': 'https://www.ville-oullins.fr', 'pop': 26000},
    {'commune': 'Villefranche-sur-Saône', 'dept': '69', 'url': 'https://www.villefranche.net', 'pop': 37000},
    {'commune': 'Givors', 'dept': '69', 'url': 'https://www.givors.fr', 'pop': 20500},
    
    # === SAVOIE (73) ===
    {'commune': 'Chambéry', 'dept': '73', 'url': 'https://www.chambery.fr', 'pop': 60000},
    {'commune': 'Aix-les-Bains', 'dept': '73', 'url': 'https://www.aixlesbains.fr', 'pop': 31000},
    {'commune': 'Albertville', 'dept': '73', 'url': 'https://www.albertville.fr', 'pop': 19000},
    {'commune': 'La Motte-Servolex', 'dept': '73', 'url': 'https://www.lamotteservolex.fr', 'pop': 12000},
    {'commune': 'Saint-Jean-de-Maurienne', 'dept': '73', 'url': 'https://www.saintjeandemaurienne.fr', 'pop': 7700},
    {'commune': 'La Ravoire', 'dept': '73', 'url': 'https://www.laravoire.fr', 'pop': 9000},
    
    # === HAUTE-SAVOIE (74) ===
    {'commune': 'Annecy', 'dept': '74', 'url': 'https://www.annecy.fr', 'pop': 130000},
    {'commune': 'Annemasse', 'dept': '74', 'url': 'https://www.annemasse.fr', 'pop': 36000},
    {'commune': 'Thonon-les-Bains', 'dept': '74', 'url': 'https://www.ville-thonon.fr', 'pop': 36000},
    {'commune': 'Cluses', 'dept': '74', 'url': 'https://www.cluses.fr', 'pop': 18000},
    {'commune': 'Sallanches', 'dept': '74', 'url': 'https://www.sallanches.fr', 'pop': 16500},
    {'commune': 'Bonneville', 'dept': '74', 'url': 'https://www.bonneville.fr', 'pop': 13000},
    {'commune': 'Rumilly', 'dept': '74', 'url': 'https://www.ville-rumilly74.fr', 'pop': 15500},
    {'commune': 'La Roche-sur-Foron', 'dept': '74', 'url': 'https://www.larochesurforon.fr', 'pop': 12000},
    {'commune': 'Saint-Julien-en-Genevois', 'dept': '74', 'url': 'https://www.st-julien-en-genevois.fr', 'pop': 16000},
    {'commune': 'Chamonix-Mont-Blanc', 'dept': '74', 'url': 'https://www.chamonix.fr', 'pop': 8900},
]

projets: List[Projet] = []

def fetch(url, timeout=8):
    try:
        r = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)}, timeout=timeout, verify=False)
        if r.status_code == 200:
            return BeautifulSoup(r.content, 'html.parser')
    except:
        pass
    return None

def analyze(url, commune, dept, pop):
    soup = fetch(url)
    if not soup:
        return None
    text = soup.get_text(separator=' ', strip=True).lower()
    mots = [m for m in MOTS_CLES if m.lower() in text]
    if not mots:
        return None
    ctx = [c for c in CONTEXTE if c.lower() in text]
    extrait = ""
    for mot in mots:
        pos = text.find(mot.lower())
        if pos != -1:
            extrait = text[max(0, pos-100):pos+200]
            break
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', soup.get_text())
    contact = emails[0] if emails else None
    return Projet(commune, dept, mots + ctx, url, extrait[:300], contact, pop)

def find_bulletins(base_url):
    urls = []
    soup = fetch(base_url)
    if soup:
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            text = link.get_text().lower()
            if any(p in href or p in text for p in ['bulletin', 'magazine', 'publication', 'actualit']):
                urls.append(urljoin(base_url, link['href']))
    return urls[:3]

print("🚀 SCRAPER SUITE - Départements 42, 43, 63, 69, 73, 74")
print(f"📊 {len(COMMUNES)} communes à scanner")
print("=" * 50)

for info in COMMUNES:
    commune, dept, base, pop = info['commune'], info['dept'], info['url'], info['pop']
    print(f"  🔍 {commune} ({dept})")
    
    # Check bulletins
    bulletin_urls = find_bulletins(base)
    if bulletin_urls:
        print(f"    📰 {len(bulletin_urls)} pages")
    
    # Analyze
    for url in [base] + bulletin_urls[:2]:
        p = analyze(url, commune, dept, pop)
        if p:
            projets.append(p)
            biomasse = any(m in ['chaufferie', 'biomasse', 'plaquettes', 'granulés', 'bois énergie', 'bois-énergie', 'réseau de chaleur', 'réseau chaleur'] for m in p.mots_cles)
            if biomasse:
                print(f"    🔥 BIOMASSE: {p.mots_cles[:4]}")
            else:
                print(f"    🎯 PROJET: {p.mots_cles[:3]}")
    
    time.sleep(random.uniform(0.5, 1))

print("\n" + "=" * 50)
print(f"📊 RÉSULTATS: {len(projets)} projets détectés")

# Filtrer les projets biomasse/réseau chaleur
biomasse_projets = [p for p in projets if any(m in ['chaufferie', 'biomasse', 'plaquettes', 'granulés', 'bois énergie', 'bois-énergie', 'réseau de chaleur', 'réseau chaleur'] for m in p.mots_cles)]

print(f"🔥 PÉPITES BIOMASSE/CHALEUR: {len(biomasse_projets)}")
for p in biomasse_projets:
    print(f"  📍 {p.commune} ({p.dept}) - {p.pop:,} hab")
    print(f"     {p.mots_cles[:5]}")
    if p.contact:
        print(f"     📧 {p.contact}")

# Sauvegarder
ts = datetime.now().strftime("%Y%m%d_%H%M")
fn = f'projets_suite_{ts}.json'
with open(fn, 'w', encoding='utf-8') as f:
    json.dump([asdict(p) for p in projets], f, ensure_ascii=False, indent=2)
print(f"\n💾 Sauvegardé: {fn}")

import urllib3
urllib3.disable_warnings()
