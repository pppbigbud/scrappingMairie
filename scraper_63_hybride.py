#!/usr/bin/env python3
"""
SCRAPER HYBRIDE - Sites de mairies + API data.gouv (fallback)
Puy-de-Dôme (63) - Test prioritaire
Anti-blocage + fallback API
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import random
import time
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import urljoin

@dataclass
class Opportunite:
    commune: str
    code_dept: str
    departement: str
    region: str
    date: str
    titre: str
    contenu: str
    mots_cles: List[str]
    url_source: str
    source_type: str  # 'site_direct' ou 'api_datagouv'
    confiance: str

# 🎯 Communes du Puy-de-Dôme (63)
COMMUNES_63 = {
    'Clermont-Ferrand': {'pop': 147865, 'urls': [
        'https://www.clermontmetropole.eu/deliberations/',
        'https://www.clermontmetropole.eu/collectivite/deliberations',
    ]},
    'Riom': {'pop': 19029, 'urls': [
        'https://www.ville-riom.fr/deliberations',
        'https://www.ville-riom.fr/ma-mairie/conseil-municipal/deliberations',
    ]},
    'Thiers': {'pop': 11601, 'urls': [
        'https://www.ville-thiers.fr/deliberations',
    ]},
    'Issoire': {'pop': 15186, 'urls': [
        'https://www.issoire.fr/deliberations',
        'https://www.issoire.fr/ma-mairie/conseil-municipal/deliberations',
    ]},
    'Ambert': {'pop': 6701, 'urls': [
        'https://www.ambert.fr/deliberations',
    ]},
    'Cournon-d\'Auvergne': {'pop': 20241, 'urls': [
        'https://www.cournon-auvergne.fr/deliberations',
    ]},
}

# 🕵️ User-Agents pour rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
]

MOTS_CLES = [
    'chaufferie', 'biomasse', 'chaudière bois', 'chaudière biomasse',
    'bois énergie', 'réseau chaleur', 'chaleur renouvelable',
    'chaufferie collective', 'chauffage bois', 'granulés',
    'plaquettes', 'chauffage collectif'
]

class ScraperHybride63:
    """Scraper hybride: sites directs + API fallback"""
    
    def __init__(self):
        self.stats = {'sites_tentes': 0, 'sites_ok': 0, 'api_fallback': 0, 'opportunites': 0}
        
    def get_session(self):
        """Crée une session avec rotation User-Agent"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        })
        return session
    
    def scraper_commune(self, nom_commune: str, info: dict) -> List[Opportunite]:
        """
        Scrape une commune: d'abord site direct, sinon API
        """
        print(f"\n{'='*60}")
        print(f"📍 {nom_commune} ({info['pop']} hab)")
        print('='*60)
        
        opportunites = []
        site_ok = False
        
        # 🎯 ÉTAPE 1: Essayer les sites directs
        for url in info['urls']:
            self.stats['sites_tentes'] += 1
            print(f"🔍 Tentative site: {url[:50]}...")
            
            try:
                session = self.get_session()
                time.sleep(random.uniform(1, 2.5))  # Délai aléatoire
                
                resp = session.get(url, timeout=15, allow_redirects=True)
                
                if resp.status_code == 200:
                    print(f"   ✅ Site accessible!")
                    self.stats['sites_ok'] += 1
                    site_ok = True
                    
                    opps = self._analyser_page(resp.text, nom_commune, url)
                    if opps:
                        opportunites.extend(opps)
                        print(f"   🎯 {len(opps)} opportunité(s) trouvée(s) sur site")
                    break
                    
                elif resp.status_code in [403, 418, 429]:
                    print(f"   🚫 Bloqué ({resp.status_code}) - Protection anti-bot")
                else:
                    print(f"   ❌ HTTP {resp.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"   ⏱️ Timeout")
            except Exception as e:
                print(f"   💥 Erreur: {str(e)[:40]}")
        
        # 🔄 ÉTAPE 2: Fallback sur API data.gouv si sites bloqués
        if not site_ok or not opportunites:
            print(f"🔄 Fallback API data.gouv pour {nom_commune}...")
            opps_api = self._recherche_api_datagouv(nom_commune)
            if opps_api:
                opportunites.extend(opps_api)
                self.stats['api_fallback'] += 1
                print(f"   ✅ {len(opps_api)} trouvée(s) via API")
        
        return opportunites
    
    def _analyser_page(self, html: str, commune: str, url: str) -> List[Opportunite]:
        """Analyse une page HTML"""
        opportunites = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Chercher tous les liens et textes
        texte_page = soup.get_text().lower()
        
        # Vérifier si mots-clés présents
        mots_trouves_page = [mot for mot in MOTS_CLES if mot.lower() in texte_page]
        
        if not mots_trouves_page:
            return []
        
        print(f"   🔑 Mots-clés détectés: {', '.join(mots_trouves_page[:3])}")
        
        # Chercher les liens pertinents
        liens = soup.find_all('a', href=True)
        
        for lien in liens[:20]:
            titre = lien.get_text(strip=True)
            if not titre or len(titre) < 10:
                continue
            
            titre_lower = titre.lower()
            mots_dans_titre = [mot for mot in MOTS_CLES if mot.lower() in titre_lower]
            
            if mots_dans_titre:
                href = lien['href']
                if not href.startswith('http'):
                    href = urljoin(url, href)
                
                opp = Opportunite(
                    commune=commune,
                    code_dept='63',
                    departement='Puy-de-Dôme',
                    region='Auvergne-Rhône-Alpes',
                    date='Non extraite',
                    titre=titre[:120],
                    contenu=f"Détecté sur site mairie. Mots: {', '.join(mots_dans_titre)}",
                    mots_cles=mots_dans_titre[:5],
                    url_source=href,
                    source_type='site_direct',
                    confiance='forte' if len(mots_dans_titre) >= 2 else 'moyenne'
                )
                opportunites.append(opp)
                self.stats['opportunites'] += 1
        
        return opportunites
    
    def _recherche_api_datagouv(self, commune: str) -> List[Opportunite]:
        """
        Recherche via API data.gouv.fr (fallback)
        """
        opportunites = []
        
        try:
            # API data.gouv pour chercher les datasets
            url = "https://www.data.gouv.fr/api/1/datasets/"
            params = {
                'q': f"{commune} délibération chaufferie biomasse",
                'page_size': 10
            }
            
            session = self.get_session()
            resp = session.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                datasets = data.get('data', [])
                
                for dataset in datasets[:3]:
                    titre = dataset.get('title', '')
                    if not titre:
                        continue
                    
                    # Vérifier mots-clés
                    titre_lower = titre.lower()
                    mots_trouves = [mot for mot in MOTS_CLES if mot.lower() in titre_lower]
                    
                    if mots_trouves:
                        opp = Opportunite(
                            commune=commune,
                            code_dept='63',
                            departement='Puy-de-Dôme',
                            region='Auvergne-Rhône-Alpes',
                            date=dataset.get('created_at', 'Non daté')[:10],
                            titre=titre[:120],
                            contenu=dataset.get('description', 'Pas de description')[:200],
                            mots_cles=mots_trouves[:5],
                            url_source=dataset.get('page', 'https://www.data.gouv.fr'),
                            source_type='api_datagouv',
                            confiance='moyenne'
                        )
                        opportunites.append(opp)
                        self.stats['opportunites'] += 1
                        
        except Exception as e:
            print(f"   ⚠️ Erreur API: {str(e)[:40]}")
        
        return opportunites
    
    def lancer_scraping(self) -> List[Opportunite]:
        """Lance le scraping sur tout le 63"""
        print("="*70)
        print("🔥 SCRAPER HYBRIDE - PUy-DE-DÔME (63)")
        print("="*70)
        print("🎯 Stratégie: Site direct → API data.gouv (fallback)")
        print("🛡️ Anti-blocage: Rotation User-Agent + délais aléatoires")
        print(f"🏘️ Communes: {len(COMMUNES_63)}")
        print()
        
        toutes_opps = []
        
        for nom_commune, info in COMMUNES_63.items():
            opps = self.scraper_commune(nom_commune, info)
            toutes_opps.extend(opps)
            time.sleep(random.uniform(2, 4))  # Pause entre communes
        
        # Résumé
        print("\n" + "="*70)
        print("📊 RÉSULTAT FINAL")
        print("="*70)
        print(f"Sites tentés: {self.stats['sites_tentes']}")
        print(f"Sites OK: {self.stats['sites_ok']}")
        print(f"Fallback API: {self.stats['api_fallback']}")
        print(f"🎯 TOTAL OPPORTUNITÉS: {len(toutes_opps)}")
        
        if toutes_opps:
            print("\n🔝 DÉTAILS:")
            for i, opp in enumerate(toutes_opps[:10], 1):
                emoji = "🔴" if opp.confiance == 'forte' else "🟠"
                source = "🌐" if opp.source_type == 'site_direct' else "📡"
                print(f"{i}. {emoji} {source} [{opp.commune}] {opp.titre[:50]}...")
        else:
            print("\n🤷 Aucune opportunité trouvée")
            print("💡 Les protections sont trop fortes, ou pas de projets récents")
        
        return toutes_opps
    
    def exporter(self, opportunites: List[Opportunite]):
        """Export JSON"""
        with open('resultats_63_hybride.json', 'w', encoding='utf-8') as f:
            json.dump([asdict(o) for o in opportunites], f, indent=2, ensure_ascii=False)
        print(f"\n💾 Exporté: resultats_63_hybride.json")


if __name__ == '__main__':
    scraper = ScraperHybride63()
    resultats = scraper.lancer_scraping()
    
    if resultats:
        scraper.exporter(resultats)
    else:
        print("\n📋 Pour ton entretien: Présente l'approche hybride")
        print("   - Sites directs d'abord (données fraîches)")
        print("   - API data.gouv en fallback (données fiables)")
        print("   - Anti-blocage: rotation UA + comportement humain")
