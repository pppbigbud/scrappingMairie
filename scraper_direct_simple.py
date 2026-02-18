#!/usr/bin/env python3
"""
SCRAPER DIRECT SIMPLE - Contournement protections sans Playwright
Utilise requests + rotation headers pour éviter les 403
Focus sur sources qui MARCHENT (RSS, sites ouverts)
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional
import time
import random
from urllib.parse import urljoin, urlparse

@dataclass
class Opportunite:
    commune: str
    departement: str
    source: str
    date: str
    titre: str
    description: str
    mots_cles: List[str]
    url_source: str
    confiance: str
    population: Optional[int] = None

# User-Agents rotation (vrais navigateurs)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# Mots-clés chaufferies
MOTS_CLES = [
    'chaufferie', 'biomasse', 'chaudière bois', 'bois énergie', 'réseau chaleur',
    'chauffage collectif', 'granulés', 'plaquettes', 'énergie renouvelable',
    'transition énergétique', 'chaudière collective', 'modernisation chauffage'
]

# Sites tests (confirmés accessibles ou RSS)
SITES_AUVERGNE = [
    # Sites qui marchaient lors des tests
    {'commune': 'Aurillac', 'dept': '15', 'url': 'https://www.aurillac.fr', 'pop': 25411, 'type': 'site'},
    {'commune': 'Le Puy-en-Velay', 'dept': '43', 'url': 'https://www.lepuyenvelay.fr/feed/', 'pop': 18618, 'type': 'rss'},
    
    # Autres URLs à tester (sites potentiellement ouverts)
    {'commune': 'Saint-Flour', 'dept': '15', 'url': 'https://www.saint-flour.fr', 'pop': 6643, 'type': 'site'},
    {'commune': 'Yssingeaux', 'dept': '43', 'url': 'https://www.yssingeaux.fr', 'pop': 7206, 'type': 'site'},
    {'commune': 'Issoire', 'dept': '63', 'url': 'https://www.issoire.fr', 'pop': 13806, 'type': 'site'},
    
    # RSS feeds supplémentaires à tester
    {'commune': 'Aurillac', 'dept': '15', 'url': 'https://www.aurillac.fr/rss', 'pop': 25411, 'type': 'rss'},
    {'commune': 'Saint-Flour', 'dept': '15', 'url': 'https://www.saint-flour.fr/rss.xml', 'pop': 6643, 'type': 'rss'},
]

# Sources alternatives (marchés publics, actualités)
SOURCES_ALTERNATIVES = [
    # Marchés publics régionaux
    {'nom': 'Marchés Auvergne', 'url': 'https://www.marches-publics.gouv.fr/rss', 'type': 'rss'},
    {'nom': 'BOAMP Auvergne', 'url': 'https://www.boamp.fr/rss/appelsoffre', 'type': 'rss'},
    
    # Actualités régionales énergie  
    {'nom': 'Région Auvergne', 'url': 'https://www.auvergnerhonealpes.fr/actualites/rss', 'type': 'rss'},
    {'nom': 'ADEME Auvergne', 'url': 'https://www.ademe.fr/rss', 'type': 'rss'},
]

class ScraperDirect:
    """Scraper direct avec contournement intelligent"""
    
    def __init__(self):
        self.session = requests.Session()
        self.resultats = []
        self.sites_testes = 0
        self.sites_ok = 0

    def get_headers_aleatoires(self) -> dict:
        """Headers aléatoires pour éviter détection"""
        return {
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
            'Referer': 'https://www.google.fr/'  # Référent Google
        }

    def analyser_texte(self, texte: str) -> tuple[List[str], str]:
        """Détection mots-clés chaufferie"""
        if not texte:
            return [], 'faible'
            
        texte_lower = texte.lower()
        mots_trouves = []
        
        for mot in MOTS_CLES:
            if mot.lower() in texte_lower:
                mots_trouves.append(mot)
        
        mots_uniques = list(set(mots_trouves))
        
        # Calcul confiance
        if len(mots_uniques) >= 3:
            confiance = 'forte'
        elif len(mots_uniques) >= 1:
            confiance = 'moyenne'
        else:
            confiance = 'faible'
            
        return mots_uniques, confiance

    def scraper_site(self, site_info: dict) -> List[Opportunite]:
        """Scrape un site avec protection anti-blocage"""
        commune = site_info['commune']
        url = site_info['url']
        
        print(f"  🌐 Test: {commune} ({url})")
        
        opportunites = []
        self.sites_testes += 1
        
        try:
            # Headers aléatoires
            headers = self.get_headers_aleatoires()
            
            # Requête avec timeout
            response = self.session.get(url, headers=headers, timeout=15, allow_redirects=True)
            
            print(f"    📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                self.sites_ok += 1
                
                # Parser le contenu
                if site_info['type'] == 'rss':
                    # RSS/XML
                    try:
                        soup = BeautifulSoup(response.content, 'xml')
                        items = soup.find_all(['item', 'entry'])[:10]  # Max 10 items RSS
                        
                        for item in items:
                            titre = ''
                            description = ''
                            link = url
                            
                            # Extraire titre
                            if item.find('title'):
                                titre = item.find('title').get_text(strip=True)
                            
                            # Extraire description
                            if item.find('description'):
                                description = item.find('description').get_text(strip=True)
                            elif item.find('summary'):
                                description = item.find('summary').get_text(strip=True)
                            
                            # Extraire lien
                            if item.find('link'):
                                if item.find('link').get_text():
                                    link = item.find('link').get_text(strip=True)
                                elif item.find('link').get('href'):
                                    link = item.find('link').get('href')
                            
                            # Analyser contenu
                            texte_complet = f"{titre} {description}"
                            mots_cles, confiance = self.analyser_texte(texte_complet)
                            
                            if mots_cles:
                                opportunites.append(Opportunite(
                                    commune=commune,
                                    departement=site_info['dept'],
                                    source='rss_feed',
                                    date=datetime.now().strftime('%Y-%m-%d'),
                                    titre=titre[:120],
                                    description=description[:400],
                                    mots_cles=mots_cles,
                                    url_source=link,
                                    confiance=confiance,
                                    population=site_info['pop']
                                ))
                                print(f"      ✅ RSS: {titre[:50]}... ({confiance})")
                                
                    except Exception as e:
                        print(f"    ⚠️ Erreur parsing RSS: {e}")
                        
                else:
                    # Site HTML normal
                    try:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Extraire texte principal
                        texte_page = soup.get_text()
                        
                        # Analyser page principale
                        mots_cles, confiance = self.analyser_texte(texte_page)
                        
                        if mots_cles:
                            opportunites.append(Opportunite(
                                commune=commune,
                                departement=site_info['dept'],
                                source='web_site',
                                date=datetime.now().strftime('%Y-%m-%d'),
                                titre=f"Site web {commune}",
                                description=f"Contenu détecté sur le site principal",
                                mots_cles=mots_cles,
                                url_source=url,
                                confiance=confiance,
                                population=site_info['pop']
                            ))
                            print(f"      ✅ SITE: Mots-clés détectés ({confiance})")
                        
                        # Chercher liens vers actualités/délibérations
                        liens_interessants = []
                        
                        for lien in soup.find_all('a', href=True)[:20]:  # Max 20 liens
                            href = lien.get('href')
                            text = lien.get_text(strip=True).lower()
                            
                            if any(mot in text for mot in ['actualité', 'délibération', 'conseil', 'publication']):
                                if href.startswith('/'):
                                    href = urljoin(url, href)
                                    
                                liens_interessants.append({
                                    'text': lien.get_text(strip=True),
                                    'url': href
                                })
                        
                        print(f"    📋 {len(liens_interessants)} liens intéressants")
                        
                        # Tester quelques liens (max 2 pour éviter surcharge)
                        for lien in liens_interessants[:2]:
                            try:
                                time.sleep(2)  # Pause respectueuse
                                
                                link_response = self.session.get(
                                    lien['url'], 
                                    headers=self.get_headers_aleatoires(), 
                                    timeout=10
                                )
                                
                                if link_response.status_code == 200:
                                    link_soup = BeautifulSoup(link_response.content, 'html.parser')
                                    link_texte = link_soup.get_text()
                                    
                                    mots_cles, confiance = self.analyser_texte(link_texte)
                                    
                                    if mots_cles:
                                        opportunites.append(Opportunite(
                                            commune=commune,
                                            departement=site_info['dept'],
                                            source='web_page',
                                            date=datetime.now().strftime('%Y-%m-%d'),
                                            titre=lien['text'][:120],
                                            description=link_texte[:400],
                                            mots_cles=mots_cles,
                                            url_source=lien['url'],
                                            confiance=confiance,
                                            population=site_info['pop']
                                        ))
                                        print(f"      ✅ PAGE: {lien['text'][:40]}... ({confiance})")
                                        
                            except Exception as e:
                                print(f"      ⚠️ Erreur lien: {e}")
                                
                    except Exception as e:
                        print(f"    ⚠️ Erreur parsing HTML: {e}")
            
            elif response.status_code == 403:
                print("    🚫 Bloqué (403 Forbidden)")
            else:
                print(f"    ❌ Erreur HTTP {response.status_code}")
                
        except Exception as e:
            print(f"    💥 Erreur requête: {e}")
            
        # Pause aléatoire entre sites
        time.sleep(random.uniform(2, 4))
        
        return opportunites

    def executer_scraping_complet(self) -> List[Opportunite]:
        """Execution complète du scraping"""
        print("🚀 DÉMARRAGE SCRAPER DIRECT SIMPLE")
        print("💡 Stratégie: Requests + BeautifulSoup avec anti-détection")
        print("🎯 Sources: Sites municipaux + RSS feeds")
        print("=" * 70)
        
        start_time = time.time()
        toutes_opportunites = []
        
        # Phase 1: Sites municipaux Auvergne
        print("🏛️ PHASE 1: SITES MUNICIPAUX AUVERGNE")
        print("=" * 50)
        
        for site in SITES_AUVERGNE:
            opportunites = self.scraper_site(site)
            toutes_opportunites.extend(opportunites)
        
        # Phase 2: Sources alternatives
        print("\n📡 PHASE 2: SOURCES ALTERNATIVES")
        print("=" * 50)
        
        for source in SOURCES_ALTERNATIVES:
            site_info = {
                'commune': source['nom'],
                'dept': 'ALT',
                'url': source['url'],
                'pop': 0,
                'type': source['type']
            }
            opportunites = self.scraper_site(site_info)
            toutes_opportunites.extend(opportunites)
        
        # Stats finales
        duree = time.time() - start_time
        print(f"\n⏱️ SCRAPING TERMINÉ EN {duree:.1f}s")
        print(f"📊 Sites testés: {self.sites_testes}")
        print(f"✅ Sites accessibles: {self.sites_ok} ({self.sites_ok/max(self.sites_testes,1)*100:.0f}%)")
        print(f"🎯 Opportunités détectées: {len(toutes_opportunites)}")
        
        return toutes_opportunites

    def generer_rapport(self, opportunites: List[Opportunite]) -> str:
        """Rapport final"""
        
        if not opportunites:
            return "❌ AUCUNE OPPORTUNITÉ DÉTECTÉE\n🔄 Suggestion: Élargir les mots-clés ou tester d'autres sources"
            
        # Stats
        stats_source = {}
        stats_confiance = {'forte': 0, 'moyenne': 0, 'faible': 0}
        stats_dept = {}
        
        for opp in opportunites:
            stats_source[opp.source] = stats_source.get(opp.source, 0) + 1
            stats_confiance[opp.confiance] += 1
            stats_dept[opp.departement] = stats_dept.get(opp.departement, 0) + 1
            
        rapport = []
        rapport.append("🎯 RAPPORT SCRAPER DIRECT - CHAUFFERIES AUVERGNE")
        rapport.append("=" * 60)
        rapport.append(f"📊 RÉSULTATS:")
        rapport.append(f"  • Total: {len(opportunites)} opportunités")
        rapport.append(f"  • Sources: {dict(stats_source)}")
        rapport.append(f"  • Confiance: Forte={stats_confiance['forte']}, Moyenne={stats_confiance['moyenne']}")
        rapport.append(f"  • Départements: {dict(stats_dept)}")
        rapport.append("")
        
        # Top opportunités
        for niveau in ['forte', 'moyenne']:
            opps_niveau = [o for o in opportunites if o.confiance == niveau]
            if opps_niveau:
                titre = f"🔥 CONFIANCE {niveau.upper()}"
                rapport.append(titre)
                rapport.append("-" * len(titre))
                
                for i, opp in enumerate(opps_niveau[:5], 1):
                    rapport.append(f"{i}. 📍 {opp.commune} ({opp.departement})")
                    rapport.append(f"   📅 {opp.date} | 🔗 {opp.source}")
                    rapport.append(f"   📰 {opp.titre}")
                    rapport.append(f"   🎯 {', '.join(opp.mots_cles)}")
                    rapport.append(f"   🌐 {opp.url_source}")
                    rapport.append("")
        
        # Bilan pour entretien
        rapport.append("💼 BILAN ENTRETIEN:")
        rapport.append("-" * 20)
        if len(opportunites) >= 3:
            rapport.append("✅ SUCCÈS - Preuve de concept validée")
            rapport.append("📈 Le scraping fonctionne sur plusieurs sources")
            rapport.append("🎯 Données exploitables pour prospection commerciale")
        else:
            rapport.append("⚠️ RÉSULTATS LIMITÉS - A améliorer")
            rapport.append("🔧 Recommandations: + de sources, + de mots-clés")
            
        return "\n".join(rapport)

def main():
    """Fonction principale"""
    scraper = ScraperDirect()
    
    # Execution
    opportunites = scraper.executer_scraping_complet()
    
    # Rapport
    rapport = scraper.generer_rapport(opportunites)
    
    print("\n" + "=" * 80)
    print("📋 RAPPORT FINAL")
    print("=" * 80)
    print(rapport)
    
    # Sauvegarde
    if opportunites:
        filename = f'chaufferies_direct_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([asdict(opp) for opp in opportunites], f, ensure_ascii=False, indent=2)
        print(f"\n💾 Sauvegardé: {filename}")

if __name__ == "__main__":
    main()