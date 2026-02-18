#!/usr/bin/env python3
"""
SCRAPER HYBRIDE FINAL - Chaufferies Biomasse Auvergne
Combine data.gouv.fr (API officielle) + Playwright (sites municipaux)
Pour maximiser la collecte d'infos sans crédit IA
"""

import requests
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Set
import time
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Opportunite:
    commune: str
    departement: str
    source: str  # 'data.gouv' ou 'site_municipal'
    date: str
    titre: str
    description: str
    mots_cles: List[str]
    url_source: str
    confiance: str  # 'forte', 'moyenne', 'faible'
    population: Optional[int] = None
    contact_email: Optional[str] = None

# Communes prioritaires Auvergne (> 5000 habitants)
COMMUNES_AUVERGNE = {
    '63': {  # Puy-de-Dôme
        'Clermont-Ferrand': {'pop': 147284, 'site': 'https://www.clermontferrand.fr'},
        'Chamalières': {'pop': 17716, 'site': 'https://www.chamalieres.fr'},
        'Cournon-d\'Auvergne': {'pop': 19627, 'site': 'https://www.cournon-auvergne.fr'},
        'Riom': {'pop': 18682, 'site': 'https://www.ville-riom.fr'},
        'Issoire': {'pop': 13806, 'site': 'https://www.issoire.fr'},
        'Thiers': {'pop': 11634, 'site': 'https://www.ville-thiers.fr'},
        'Ceyrat': {'pop': 6156, 'site': 'https://www.ceyrat.fr'},
        'Beaumont': {'pop': 11334, 'site': 'https://www.beaumont63.fr'},
        'Gerzat': {'pop': 9865, 'site': 'https://www.gerzat.fr'},
        'Aubière': {'pop': 10239, 'site': 'https://www.aubiere.fr'}
    },
    '03': {  # Allier
        'Vichy': {'pop': 25789, 'site': 'https://www.ville-vichy.fr'},
        'Montluçon': {'pop': 37570, 'site': 'https://www.montlucon.fr'},
        'Moulins': {'pop': 19960, 'site': 'https://www.moulins.fr'},
        'Cusset': {'pop': 12617, 'site': 'https://www.cusset.fr'},
        'Yzeure': {'pop': 12760, 'site': 'https://www.yzeure.fr'}
    },
    '15': {  # Cantal
        'Aurillac': {'pop': 25411, 'site': 'https://www.aurillac.fr'},
        'Saint-Flour': {'pop': 6643, 'site': 'https://www.saint-flour.fr'},
        'Arpajon-sur-Cère': {'pop': 6291, 'site': 'https://www.arpajon-sur-cere.fr'}
    },
    '43': {  # Haute-Loire
        'Le Puy-en-Velay': {'pop': 18618, 'site': 'https://www.lepuyenvelay.fr'},
        'Monistrol-sur-Loire': {'pop': 9694, 'site': 'https://www.monistrolsurloire.fr'},
        'Yssingeaux': {'pop': 7206, 'site': 'https://www.yssingeaux.fr'}
    }
}

# Mots-clés détection
MOTS_CLES_PRIORITAIRES = [
    'chaufferie', 'biomasse', 'chaudière bois', 'bois énergie', 'réseau chaleur',
    'chaufferie collective', 'chaudière biomasse', 'chaleur renouvelable'
]

MOTS_CLES_SECONDAIRES = [
    'chauffage collectif', 'granulés', 'plaquettes', 'modernisation chauffage',
    'remplacement chaudière', 'énergie renouvelable', 'transition énergétique'
]

class ScraperHybride:
    """Scraper combinant data.gouv.fr + Playwright"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.resultats = []
        self.communes_traitees = set()

    def analyser_texte(self, texte: str) -> tuple[List[str], str]:
        """Analyse le texte pour détecter mots-clés et niveau confiance"""
        if not texte:
            return [], 'faible'
            
        texte_lower = texte.lower()
        mots_trouves = []
        
        # Recherche mots-clés prioritaires
        for mot in MOTS_CLES_PRIORITAIRES:
            if mot.lower() in texte_lower:
                mots_trouves.append(mot)
                
        # Recherche mots-clés secondaires
        for mot in MOTS_CLES_SECONDAIRES:
            if mot.lower() in texte_lower:
                mots_trouves.append(mot)
        
        # Déterminer confiance
        if len(mots_trouves) >= 3:
            confiance = 'forte'
        elif len(mots_trouves) >= 1:
            confiance = 'moyenne'
        else:
            confiance = 'faible'
            
        return mots_trouves, confiance

    async def scraper_data_gouv(self, departement: str) -> List[Opportunite]:
        """Scraper via API data.gouv.fr"""
        logger.info(f"🔍 Recherche data.gouv.fr pour le département {departement}")
        
        opportunites = []
        
        # API des actes des collectivités
        url = "https://www.data.gouv.fr/api/1/datasets/"
        params = {
            'q': f'délibération {departement} chaufferie biomasse',
            'page_size': 50
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ {len(data.get('data', []))} datasets trouvés")
                
                for dataset in data.get('data', [])[:10]:  # Limite pour test
                    title = dataset.get('title', '')
                    description = dataset.get('description', '')
                    
                    mots_cles, confiance = self.analyser_texte(f"{title} {description}")
                    
                    if mots_cles:  # Si mots-clés trouvés
                        opportunites.append(Opportunite(
                            commune=f"Dataset-{dataset.get('slug', 'unknown')[:20]}",
                            departement=departement,
                            source='data.gouv',
                            date=dataset.get('created_at', '')[:10],
                            titre=title[:100],
                            description=description[:300],
                            mots_cles=mots_cles,
                            url_source=f"https://www.data.gouv.fr/fr/datasets/{dataset.get('slug', '')}",
                            confiance=confiance
                        ))
                        
        except Exception as e:
            logger.error(f"❌ Erreur data.gouv.fr: {e}")
            
        return opportunites

    async def scraper_site_municipal(self, commune: str, info: dict, departement: str) -> List[Opportunite]:
        """Scraper un site municipal avec Playwright"""
        logger.info(f"🌐 Scraping site {commune}: {info['site']}")
        
        opportunites = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Headers anti-détection
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
                })
                
                # Visiter la page principale
                await page.goto(info['site'], timeout=15000)
                await page.wait_for_timeout(2000)  # Attendre le chargement
                
                # Rechercher liens vers délibérations/actualités
                liens_interessants = await page.evaluate('''
                    () => {
                        const liens = [];
                        const selectors = [
                            'a[href*="deliberation"]', 'a[href*="conseil"]', 'a[href*="actualit"]',
                            'a[href*="info"]', 'a[href*="municipal"]', 'a[text()*="Délibération"]'
                        ];
                        
                        selectors.forEach(selector => {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(el => {
                                const text = el.textContent.toLowerCase();
                                const href = el.href;
                                if (text && href && (
                                    text.includes('délibération') || 
                                    text.includes('conseil') || 
                                    text.includes('actualité')
                                )) {
                                    liens.push({text: el.textContent.trim(), url: href});
                                }
                            });
                        });
                        
                        return liens.slice(0, 5); // Max 5 liens par site
                    }
                ''')
                
                logger.info(f"  📋 {len(liens_interessants)} liens trouvés pour {commune}")
                
                # Visiter chaque lien intéressant
                for lien in liens_interessants:
                    try:
                        await page.goto(lien['url'], timeout=10000)
                        await page.wait_for_timeout(1000)
                        
                        # Extraire le contenu
                        contenu = await page.evaluate('() => document.body.innerText')
                        
                        mots_cles, confiance = self.analyser_texte(contenu)
                        
                        if mots_cles:  # Si pertinent
                            opportunites.append(Opportunite(
                                commune=commune,
                                departement=departement,
                                source='site_municipal',
                                date=datetime.now().strftime('%Y-%m-%d'),
                                titre=lien['text'][:100],
                                description=contenu[:400],
                                mots_cles=mots_cles,
                                url_source=lien['url'],
                                confiance=confiance,
                                population=info['pop']
                            ))
                            logger.info(f"  ✅ Opportunité trouvée: {lien['text'][:50]}...")
                            
                    except Exception as e:
                        logger.warning(f"  ⚠️ Erreur sur {lien['url']}: {e}")
                        continue
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"❌ Erreur scraping {commune}: {e}")
            
        return opportunites

    async def executer_scraping_complet(self, departements: List[str] = ['63', '03', '15', '43']) -> List[Opportunite]:
        """Execute le scraping hybride complet"""
        logger.info(f"🚀 DÉMARRAGE SCRAPING HYBRIDE - Départements: {', '.join(departements)}")
        
        tous_resultats = []
        
        # 1. Scraping data.gouv.fr pour chaque département
        logger.info("=" * 60)
        logger.info("🏛️  PHASE 1: API DATA.GOUV.FR")
        logger.info("=" * 60)
        
        for dept in departements:
            resultats_api = await self.scraper_data_gouv(dept)
            tous_resultats.extend(resultats_api)
            logger.info(f"📊 Département {dept}: {len(resultats_api)} opportunités trouvées")
            await asyncio.sleep(1)  # Pause entre requêtes
            
        # 2. Scraping sites municipaux
        logger.info("=" * 60)
        logger.info("🌐 PHASE 2: SITES MUNICIPAUX (PLAYWRIGHT)")  
        logger.info("=" * 60)
        
        for dept, communes in COMMUNES_AUVERGNE.items():
            if dept in departements:
                logger.info(f"🏛️  Traitement département {dept}: {len(communes)} communes")
                
                for commune, info in list(communes.items())[:3]:  # Limite 3 par dept pour test
                    try:
                        resultats_site = await self.scraper_site_municipal(commune, info, dept)
                        tous_resultats.extend(resultats_site)
                        logger.info(f"  📍 {commune}: {len(resultats_site)} opportunités")
                        await asyncio.sleep(3)  # Pause entre sites
                        
                    except Exception as e:
                        logger.error(f"  ❌ {commune}: {e}")
                        
        return tous_resultats

    def generer_rapport(self, opportunites: List[Opportunite]) -> str:
        """Génère un rapport détaillé"""
        
        if not opportunites:
            return "❌ Aucune opportunité détectée"
            
        # Stats par source
        stats_source = {}
        stats_confiance = {'forte': 0, 'moyenne': 0, 'faible': 0}
        
        for opp in opportunites:
            stats_source[opp.source] = stats_source.get(opp.source, 0) + 1
            stats_confiance[opp.confiance] += 1
            
        rapport = []
        rapport.append("🎯 RAPPORT FINAL - SCRAPING HYBRIDE CHAUFFERIES BIOMASSE")
        rapport.append("=" * 70)
        rapport.append(f"📊 STATISTIQUES GÉNÉRALES")
        rapport.append(f"  • Total opportunités: {len(opportunites)}")
        rapport.append(f"  • Sources: {dict(stats_source)}")
        rapport.append(f"  • Confiance: Forte={stats_confiance['forte']}, Moyenne={stats_confiance['moyenne']}, Faible={stats_confiance['faible']}")
        rapport.append("")
        
        # Top opportunités par confiance
        rapport.append("🔥 TOP OPPORTUNITÉS (CONFIANCE FORTE)")
        rapport.append("-" * 50)
        
        fortes = [o for o in opportunites if o.confiance == 'forte'][:10]
        for i, opp in enumerate(fortes, 1):
            rapport.append(f"{i}. 📍 {opp.commune} ({opp.departement})")
            rapport.append(f"   📅 {opp.date} | 🔗 {opp.source}")
            rapport.append(f"   📰 {opp.titre}")
            rapport.append(f"   🎯 Mots-clés: {', '.join(opp.mots_cles)}")
            rapport.append(f"   🌐 {opp.url_source}")
            rapport.append("")
            
        # Moyennes confiance
        rapport.append("⚡ OPPORTUNITÉS MOYENNES")
        rapport.append("-" * 30)
        
        moyennes = [o for o in opportunites if o.confiance == 'moyenne'][:5]
        for i, opp in enumerate(moyennes, 1):
            rapport.append(f"{i}. {opp.commune} - {opp.titre[:60]}...")
            
        return "\n".join(rapport)

async def main():
    """Fonction principale"""
    scraper = ScraperHybride()
    
    # Lancement scraping complet
    start_time = time.time()
    opportunites = await scraper.executer_scraping_complet(['63'])  # Test sur Puy-de-Dôme uniquement
    
    # Génération rapport
    rapport = scraper.generer_rapport(opportunites)
    
    print("\n" + "=" * 80)
    print(f"⏱️  SCRAPING TERMINÉ EN {time.time() - start_time:.1f}s")
    print("=" * 80)
    print(rapport)
    
    # Sauvegarde JSON
    with open(f'opportunites_hybrides_{datetime.now().strftime("%Y%m%d_%H%M")}.json', 'w', encoding='utf-8') as f:
        json.dump([asdict(opp) for opp in opportunites], f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Données sauvegardées: opportunites_hybrides_{datetime.now().strftime('%Y%m%d_%H%M')}.json")

if __name__ == "__main__":
    asyncio.run(main())