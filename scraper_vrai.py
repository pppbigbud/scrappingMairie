#!/usr/bin/env python3
"""
SCRAPER VRAI - Plus grandes agglomérations françaises
Cible les sites de mairies des préfectures et sous-préfectures
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from dataclasses import dataclass, asdict
from typing import List, Optional
import time
from urllib.parse import urljoin, urlparse

@dataclass 
class Opportunite:
    commune: str
    departement: str
    date: str
    titre: str
    contenu: str
    mots_cles: List[str]
    url_source: str
    confiance: str

# 🏛️ PLUS GRANDES AGGLOMÉRATIONS FRANÇAISES
# Liste des préfectures et grandes villes avec leurs URLs de délibérations
VILLES_CIBLES = {
    # Métropoles (> 500 000 hab)
    'Marseille': {
        'dept': '13', 'region': 'Provence-Alpes-Côte d\'Azur',
        'urls': [
            'https://www.marseille.fr/mairie/deliberations-du-conseil-municipal',
        ]
    },
    'Lyon': {
        'dept': '69', 'region': 'Auvergne-Rhône-Alpes',
        'urls': [
            'https://www.lyon.fr/demarche/deliberations-conseil-municipal',
        ]
    },
    'Toulouse': {
        'dept': '31', 'region': 'Occitanie',
        'urls': [
            'https://www.toulouse.fr/web/decouverte/deliberations',
        ]
    },
    'Nice': {
        'dept': '06', 'region': 'Provence-Alpes-Côte d\'Azur',
        'urls': [
            'http://deliberations.nice.fr/',
        ]
    },
    'Nantes': {
        'dept': '44', 'region': 'Pays de la Loire',
        'urls': [
            'https://www.nantes.fr/home/demarche/deliberations.html',
        ]
    },
    'Strasbourg': {
        'dept': '67', 'region': 'Grand Est',
        'urls': [
            'https://www.strasbourg.eu/deliberations-conseil-municipal',
        ]
    },
    'Montpellier': {
        'dept': '34', 'region': 'Occitanie',
        'urls': [
            'https://www.montpellier.fr/4027-deliberations-du-conseil-municipal.htm',
        ]
    },
    'Bordeaux': {
        'dept': '33', 'region': 'Nouvelle-Aquitaine',
        'urls': [
            'https://www.bordeaux.fr/o43771/deliberations',
        ]
    },
    'Lille': {
        'dept': '59', 'region': 'Hauts-de-France',
        'urls': [
            'https://www.lille.fr/Nos-dossiers/La-vie-communale/Les-deliberations',
        ]
    },
    # Villes moyennes importantes (100 000 - 500 000 hab)
    'Rennes': {
        'dept': '35', 'region': 'Bretagne',
        'urls': [
            'https://metropole.rennes.fr/les-deliberations',
        ]
    },
    'Reims': {
        'dept': '51', 'region': 'Grand Est',
        'urls': [
            'https://www.reims.fr/municipalite/les-elus/conseil-municipal/les-deliberations',
        ]
    },
    'Toulon': {
        'dept': '83', 'region': 'Provence-Alpes-Côte d\'Azur',
        'urls': [
            'https://www.toulon.fr/decouvrir-la-ville/mairie-deliberations.html',
        ]
    },
    'Grenoble': {
        'dept': '38', 'region': 'Auvergne-Rhône-Alpes',
        'urls': [
            'https://www.grenoble.fr/deliberations-du-conseil-municipal-de-grenoble',
        ]
    },
    'Dijon': {
        'dept': '21', 'region': 'Bourgogne-Franche-Comté',
        'urls': [
            'https://www.dijon.fr/conseil-municipal-et-comite-metropolitain/conseil-municipal/les-deliberations',
        ]
    },
    'Angers': {
        'dept': '49', 'region': 'Pays de la Loire',
        'urls': [
            'https://www.angers.fr/lactu-municipale/les-deliberations/index.html',
        ]
    },
}

MOTS_CLES = [
    'chaufferie', 'biomasse', 'chaudière bois', 'chaudière biomasse',
    'bois énergie', 'réseau chaleur', 'chaleur renouvelable',
    'chaufferie collective', 'chauffage bois', 'granulés',
    'plaquettes forestières', 'chaudière granulés'
]

class ScraperVrai:
    """Vrai scraping des sites de mairies"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.opportunites = []
        
    def scraper_ville(self, ville: str, config: dict) -> List[Opportunite]:
        """
        Scraping d'une ville - tente toutes les URLs fournies
        """
        print(f"\n🏙️ [{ville}] ({config['dept']})")
        print("-" * 60)
        
        opportunites = []
        
        for url in config['urls']:
            try:
                print(f"🔍 {url}")
                resp = self.session.get(url, timeout=20, allow_redirects=True)
                
                if resp.status_code == 200:
                    opps = self._analyser_page(resp.text, ville, config, url)
                    if opps:
                        opportunites.extend(opps)
                        print(f"   ✅ {len(opps)} opportunité(s)")
                    else:
                        print(f"   ⚠️ Aucune opportunité trouvée")
                else:
                    print(f"   ❌ Erreur {resp.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"   ⏱️ Timeout")
            except Exception as e:
                print(f"   💥 Erreur: {str(e)[:50]}")
            
            time.sleep(1)  # Respecter les serveurs
        
        return opportunites
    
    def _analyser_page(self, html: str, ville: str, config: dict, url_source: str) -> List[Opportunite]:
        """Analyse une page HTML pour trouver les délibérations"""
        opportunites = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Chercher tous les liens qui pourraient être des délibérations
        # Pattern 1: Liens avec "deliberation", "conseil", "actes" dans le href
        liens = soup.find_all('a', href=re.compile(r'deliberation|conseil|actes|pv|document', re.I))
        
        # Pattern 2: Divs qui contiennent les termes recherchés
        # On cherche dans tout le texte de la page
        texte_complet = soup.get_text().lower()
        
        # Vérifier si au moins un mot-clé est présent
        mots_trouves_page = []
        for mot in MOTS_CLES:
            if mot.lower() in texte_complet[:50000]:  # Limite à 50k caractères
                mots_trouves_page.append(mot)
        
        if mots_trouves_page:
            print(f"   🔑 Mots-clés trouvés sur la page: {', '.join(mots_trouves_page[:3])}")
        
        # Pour chaque lien, vérifier s'il contient des mots-clés
        for lien in liens[:20]:  # Limiter à 20 liens pour le POC
            try:
                titre = lien.get_text(strip=True)
                href = lien.get('href', '')
                
                if not titre or len(titre) < 5:
                    continue
                
                # Chercher les mots-clés dans le titre
                titre_lower = titre.lower()
                mots_trouves = []
                
                for mot in MOTS_CLES:
                    if mot.lower() in titre_lower:
                        nb_mots = len(titre_lower.split())
                        if nb_mots < 100:  # Vérifier que c'est un titre court
                            mots_trouves.append(mot)
                
                if mots_trouves:
                    # Construire URL complète
                    if href.startswith('http'):
                        url_complete = href
                    else:
                        url_complete = urljoin(url_source, href)
                    
                    # Déterminer confiance
                    confiance = 'forte' if len(mots_trouves) >= 2 else 'moyenne'
                    
                    opp = Opportunite(
                        commune=ville,
                        departement=f"{config['dept']} - {config['region']}",
                        date="Date non extraite",
                        titre=titre[:150],
                        contenu=f"Projet détecté via scraping: {titre}",
                        mots_cles=mots_trouves[:5],
                        url_source=url_complete,
                        confiance=confiance
                    )
                    opportunites.append(opp)
                    
            except Exception:
                continue
        
        return opportunites
    
    def lancer_veille_nationale(self, max_villes: int = 10) -> List[Opportunite]:
        """
        Lance la veille sur les X plus grandes villes
        """
        print("=" * 70)
        print("🔥 VRAI SCRAPING - PLUS GRANDES AGGLOMÉRATIONS")
        print("=" * 70)
        print(f"🎯 {min(max_villes, len(VILLES_CIBLES))} villes à analyser")
        print("🏛️ Cible: Préfectures et grandes villes")
        print("⏱️ Temps estimé: 2-3 minutes")
        print()
        
        toutes_opps = []
        villes_list = list(VILLES_CIBLES.items())[:max_villes]
        
        for i, (ville, config) in enumerate(villes_list, 1):
            print(f"\n[{i}/{len(villes_list)}] ", end="")
            opps = self.scraper_ville(ville, config)
            toutes_opps.extend(opps)
        
        print("\n" + "=" * 70)
        print(f"📊 RÉSULTAT: {len(toutes_opps)} opportunités trouvées")
        print("=" * 70)
        
        if toutes_opps:
            print("\n🎯 TOP RÉSULTATS:")
            for i, opp in enumerate(toutes_opps[:5], 1):
                emoji = "🔴" if opp.confiance == "forte" else "🟠"
                print(f"{i}. {emoji} {opp.commune}: {opp.titre[:60]}...")
        
        return toutes_opps


def main():
    """Test CLI"""
    scraper = ScraperVrai()
    resultats = scraper.lancer_veille_nationale(max_villes=15)
    
    if resultats:
        print(f"\n💾 {len(resultats)} opportunités exportées")
    else:
        print("\n🤷 Aucune opportunité trouvée")
        print("💡 Les sites peuvent bloquer le scraping ou changer de structure")


if __name__ == '__main__':
    main()
