#!/usr/bin/env python3
"""
SCRAPER AUVERGNE-RHÔNE-ALPES - VERSION COMPLÈTE
Toutes communes > 5000 habitants - 12 départements
~240 communes couvertes
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
import time
from urllib.parse import urljoin
import sys

# Ajouter le fichier de communes
sys.path.insert(0, '/home/ubuntu/.openclaw/workspace')
from communes_aura_complete import COMMUNES_AUVERGNE_RHONE_ALPES

@dataclass 
class Opportunite:
    commune: str
    code_dept: str
    departement: str
    region: str
    population: int
    date: str
    titre: str
    contenu: str
    mots_cles: List[str]
    url_source: str
    confiance: str

# Mots-clés pour détection
MOTS_CLES = [
    'chaufferie', 'biomasse', 'chaudière bois', 'chaudière biomasse',
    'bois énergie', 'réseau chaleur', 'chaleur renouvelable',
    'chaufferie collective', 'chauffage bois', 'granulés',
    'plaquettes forestières', 'chaudière granulés', 'chauffage collectif'
]

class ScraperAuvergneRhoneAlpes:
    """Scraper exhaustif pour l'Auvergne-Rhône-Alpes"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.opportunites = []
        self.stats = {'testees': 0, 'avec_url': 0, 'succes': 0, 'opportunites': 0}
        
    def scraper_departement(self, code_dept: str, max_communes: int = None) -> List[Opportunite]:
        """Scrape un département entier"""
        if code_dept not in COMMUNES_AUVERGNE_RHONE_ALPES:
            print(f"❌ Département {code_dept} non trouvé")
            return []
        
        dept_info = COMMUNES_AUVERGNE_RHONE_ALPES[code_dept]
        print(f"\n{'='*70}")
        print(f"📍 DÉPARTEMENT: {dept_info['nom']} ({code_dept})")
        print(f"🌄 Région: {dept_info['region']}")
        print(f"🏘️ Communes: {len(dept_info['communes'])}")
        print('='*70)
        
        opportunites = []
        communes = dept_info['communes'][:max_communes] if max_communes else dept_info['communes']
        
        for i, commune_info in enumerate(communes, 1):
            self.stats['testees'] += 1
            
            # Filtrer par population (> 5000)
            if commune_info.get('pop', 0) < 5000:
                continue
            
            print(f"\n[{i}/{len(communes)}] {commune_info['nom']} ({commune_info.get('pop', 'N/A')} hab)")
            
            # Si on a une URL directe, l'utiliser
            if commune_info.get('url'):
                self.stats['avec_url'] += 1
                opps = self._scraper_url_directe(commune_info, code_dept, dept_info)
                if opps:
                    opportunites.extend(opps)
                    print(f"   ✅ {len(opps)} opportunité(s)")
            else:
                # Sinon, essayer de deviner l'URL standard
                opps = self._scraper_url_standard(commune_info, code_dept, dept_info)
                if opps:
                    opportunites.extend(opps)
            
            time.sleep(0.3)  # Respecter les serveurs
        
        return opportunites
    
    def _scraper_url_directe(self, commune_info: dict, code_dept: str, dept_info: dict) -> List[Opportunite]:
        """Scrape une commune avec URL connue"""
        url = commune_info['url']
        nom_commune = commune_info['nom']
        
        try:
            resp = self.session.get(url, timeout=15)
            self.stats['succes'] += 1
            
            if resp.status_code == 200:
                return self._analyser_page(resp.text, nom_commune, code_dept, dept_info, url)
            else:
                print(f"   ❌ HTTP {resp.status_code}")
                return []
                
        except Exception as e:
            print(f"   💥 Erreur: {str(e)[:40]}")
            return []
    
    def _scraper_url_standard(self, commune_info: dict, code_dept: str, dept_info: dict) -> List[Opportunite]:
        """Tente de deviner et scraper l'URL standard d'une mairie"""
        nom = commune_info['nom'].lower().replace("'", "-").replace(" ", "-")
        urls_tentatives = [
            f"https://www.{nom}.fr/deliberations",
            f"https://www.mairie-{nom}.fr/documents",
            f"https://{nom}.fr/les-deliberations",
        ]
        
        for url in urls_tentatives:
            try:
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    print(f"   🔍 URL trouvée: {url[:50]}...")
                    return self._analyser_page(resp.text, commune_info['nom'], code_dept, dept_info, url)
            except:
                continue
        
        return []
    
    def _analyser_page(self, html: str, commune: str, code_dept: str, dept_info: dict, url: str) -> List[Opportunite]:
        """Analyse une page pour trouver des opportunités"""
        opportunites = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Chercher dans le texte complet
        texte = soup.get_text().lower()
        
        # Trouver les mots-clés présents
        mots_trouves = []
        for mot in MOTS_CLES:
            if mot.lower() in texte:
                mots_trouves.append(mot)
        
        if not mots_trouves:
            return []
        
        # Chercher les liens pertinents
        liens = soup.find_all('a', href=True)
        
        for lien in liens[:15]:
            titre = lien.get_text(strip=True)
            if not titre or len(titre) < 10:
                continue
            
            titre_lower = titre.lower()
            mots_dans_titre = []
            
            for mot in MOTS_CLES:
                if mot.lower() in titre_lower:
                    mots_dans_titre.append(mot)
            
            if mots_dans_titre:
                href = lien['href']
                if not href.startswith('http'):
                    href = urljoin(url, href)
                
                confiance = 'forte' if len(mots_dans_titre) >= 2 else 'moyenne'
                
                opp = Opportunite(
                    commune=commune,
                    code_dept=code_dept,
                    departement=dept_info['nom'],
                    region=dept_info['region'],
                    population=0,
                    date="Non extraite",
                    titre=titre[:120],
                    contenu=f"Mots-clés trouvés: {', '.join(mots_dans_titre)}",
                    mots_cles=mots_dans_titre[:5],
                    url_source=href,
                    confiance=confiance
                )
                opportunites.append(opp)
                self.stats['opportunites'] += 1
        
        return opportunites
    
    def lancer_veille_region(self, dept_cibles: List[str] = None, max_communes_par_dept: int = None) -> List[Opportunite]:
        """
        Lance la veille sur toute la région ou départements sélectionnés
        """
        print("="*70)
        print("🔥 SCRAPING AUVERGNE-RHÔNE-ALPES - MODE EXHAUSTIF")
        print("="*70)
        print(f"🎯 Objectif: Toutes communes > 5000 habitants")
        print(f"📊 Total départements: {len(COMMUNES_AUVERGNE_RHONE_ALPES)}")
        print()
        
        toutes_opps = []
        
        # Départements à scraper
        if dept_cibles:
            depts = [d for d in dept_cibles if d in COMMUNES_AUVERGNE_RHONE_ALPES]
        else:
            depts = list(COMMUNES_AUVERGNE_RHONE_ALPES.keys())
        
        print(f"🗺️ Départements sélectionnés: {', '.join(depts)}")
        print()
        
        for code_dept in depts:
            opps = self.scraper_departement(code_dept, max_communes_par_dept)
            toutes_opps.extend(opps)
            print(f"\n📈 {dept_info['nom']}: {len(opps)} opportunités")
        
        # Résumé final
        print("\n" + "="*70)
        print("📊 RÉSULTAT FINAL")
        print("="*70)
        print(f"Communes testées: {self.stats['testees']}")
        print(f"Avec URL connue: {self.stats['avec_url']}")
        print(f"Connexions réussies: {self.stats['succes']}")
        print(f"🎯 Opportunités trouvées: {len(toutes_opps)}")
        
        if toutes_opps:
            print("\n🔝 TOP 10:")
            for i, opp in enumerate(toutes_opps[:10], 1):
                emoji = "🔴" if opp.confiance == "forte" else "🟠"
                print(f"{i}. {emoji} [{opp.departement}] {opp.commune}: {opp.titre[:50]}...")
        
        return toutes_opps
    
    def exporter(self, opportunites: List[Opportunite], filename: str = "resultats_aura.json"):
        """Exporte les résultats"""
        data = [asdict(opp) for opp in opportunites]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Exporté: {filename}")


# Pour tester en CLI
if __name__ == '__main__':
    scraper = ScraperAuvergneRhoneAlpes()
    
    # Test rapide sur un département
    resultats = scraper.lancer_veille_region(dept_cibles=['63'], max_communes_par_dept=5)
    
    if resultats:
        scraper.exporter(resultats)
