#!/usr/bin/env python3
"""
SCRAPER HYBRIDE COMPLET - Solutions 1 & 2 combinées
1. API data.gouv.fr corrigée (légal, fiable) 
2. Playwright pour sites protégés (contournement 403)
"""

import requests
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
import time
import asyncio
import sys
import os

# Import conditionnel de Playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright non disponible - mode API uniquement")

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

# Communes Auvergne prioritaires
COMMUNES_AUVERGNE = {
    '63': {  # Puy-de-Dôme
        'Clermont-Ferrand': {'pop': 147284, 'site': 'https://www.clermontferrand.fr'},
        'Chamalières': {'pop': 17716, 'site': 'https://www.chamalieres.fr'},
        'Cournon-d\'Auvergne': {'pop': 19627, 'site': 'https://www.cournon-auvergne.fr'},
        'Riom': {'pop': 18682, 'site': 'https://www.ville-riom.fr'},
        'Issoire': {'pop': 13806, 'site': 'https://www.issoire.fr'},
        'Aubière': {'pop': 10239, 'site': 'https://www.aubiere.fr'},
        'Beaumont': {'pop': 11334, 'site': 'https://www.beaumont63.fr'}
    },
    '03': {  # Allier  
        'Vichy': {'pop': 25789, 'site': 'https://www.ville-vichy.fr'},
        'Montluçon': {'pop': 37570, 'site': 'https://www.montlucon.fr'},
        'Moulins': {'pop': 19960, 'site': 'https://www.moulins.fr'}
    },
    '15': {  # Cantal
        'Aurillac': {'pop': 25411, 'site': 'https://www.aurillac.fr'},
        'Saint-Flour': {'pop': 6643, 'site': 'https://www.saint-flour.fr'}
    },
    '43': {  # Haute-Loire
        'Le Puy-en-Velay': {'pop': 18618, 'site': 'https://www.lepuyenvelay.fr'}
    }
}

# Mots-clés optimisés
MOTS_CLES_PRIORITAIRES = [
    'chaufferie', 'biomasse', 'chaudière bois', 'bois énergie', 
    'réseau chaleur', 'chaufferie collective', 'chaudière biomasse'
]

MOTS_CLES_SECONDAIRES = [
    'chauffage collectif', 'granulés', 'plaquettes', 'modernisation chauffage',
    'énergie renouvelable', 'transition énergétique', 'remplacement chaudière'
]

class ScraperHybride:
    """Scraper combinant API data.gouv.fr corrigée + Playwright"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.resultats = []

    def analyser_texte(self, texte: str) -> tuple[List[str], str]:
        """Analyse texte pour détecter mots-clés chaufferie"""
        if not texte:
            return [], 'faible'
            
        texte_lower = texte.lower()
        mots_trouves = []
        
        # Recherche prioritaires  
        for mot in MOTS_CLES_PRIORITAIRES:
            if mot.lower() in texte_lower:
                mots_trouves.append(mot)
                
        # Recherche secondaires
        for mot in MOTS_CLES_SECONDAIRES:
            if mot.lower() in texte_lower:
                mots_trouves.append(mot)
        
        # Calcul confiance
        mots_uniques = list(set(mots_trouves))
        if len(mots_uniques) >= 3:
            confiance = 'forte'
        elif len(mots_uniques) >= 1:
            confiance = 'moyenne'  
        else:
            confiance = 'faible'
            
        return mots_uniques, confiance

    def scraper_data_gouv_corrige(self) -> List[Opportunite]:
        """API data.gouv.fr avec requête corrigée"""
        print("🏛️ PHASE 1: API DATA.GOUV.FR CORRIGÉE")
        print("=" * 50)
        
        opportunites = []
        
        # URL corrigée avec bons paramètres
        url = "https://www.data.gouv.fr/api/1/datasets/"
        
        # Mots-clés spécifiques pour chaufferies
        termes_recherche = [
            'chaufferie',
            'biomasse énergie', 
            'délibération énergie',
            'conseil municipal chauffage',
            'marché chaufferie',
            'bois énergie'
        ]
        
        for terme in termes_recherche:
            print(f"🔍 Recherche: '{terme}'")
            
            params = {
                'q': terme,
                'page_size': 15,
                'sort': '-created_at',
                'format': 'json'
            }
            
            try:
                response = self.session.get(url, params=params, timeout=15)
                print(f"  📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    datasets = data.get('data', [])
                    print(f"  📋 {len(datasets)} datasets trouvés")
                    
                    for dataset in datasets:
                        title = dataset.get('title', '')
                        description = dataset.get('description', '')
                        organization = dataset.get('organization', {}) or {}
                        
                        # Analyser contenu
                        texte_complet = f"{title} {description}"
                        mots_cles, confiance = self.analyser_texte(texte_complet)
                        
                        if mots_cles and confiance in ['forte', 'moyenne']:
                            opportunites.append(Opportunite(
                                commune=organization.get('name', 'Organisation inconnue')[:50],
                                departement='Multi',
                                source='data.gouv.fr',
                                date=dataset.get('created_at', '')[:10],
                                titre=title[:120],
                                description=description[:400],
                                mots_cles=mots_cles,
                                url_source=f"https://www.data.gouv.fr/fr/datasets/{dataset.get('slug', '')}",
                                confiance=confiance
                            ))
                            print(f"    ✅ TROUVÉ: {title[:60]}... (confiance: {confiance})")
                            
                else:
                    print(f"  ❌ Erreur HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"  ⚠️ Erreur: {e}")
                
            time.sleep(1.5)  # Pause respectueuse
            
        print(f"📊 Total API data.gouv.fr: {len(opportunites)} opportunités\n")
        return opportunites

    async def scraper_playwright(self) -> List[Opportunite]:
        """Scraping avec Playwright pour contourner protections"""
        if not PLAYWRIGHT_AVAILABLE:
            print("❌ Playwright non disponible - installation requise")
            return []
            
        print("🌐 PHASE 2: PLAYWRIGHT ANTI-BLOCAGE") 
        print("=" * 50)
        
        opportunites = []
        
        try:
            async with async_playwright() as p:
                # Lancer navigateur avec options furtives
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='fr-FR',
                    timezone_id='Europe/Paris',
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                # Masquer automation
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = {runtime: {}};
                """)
                
                # Tester communes une par une
                for dept, communes in COMMUNES_AUVERGNE.items():
                    print(f"🏛️ Département {dept}: {len(communes)} communes")
                    
                    for commune, info in list(communes.items())[:2]:  # Limite 2 par dept pour test
                        print(f"  🌐 Traitement: {commune}")
                        
                        try:
                            # Naviguer vers le site
                            await page.goto(info['site'], timeout=20000, wait_until='networkidle')
                            await page.wait_for_timeout(2000)
                            
                            # Chercher liens pertinents
                            liens_interessants = await page.evaluate('''
                                () => {
                                    const liens = [];
                                    const selectors = [
                                        'a[href*="deliberation"]', 'a[href*="conseil"]', 
                                        'a[href*="actualit"]', 'a[href*="info"]',
                                        'a:has-text("Délibération")', 'a:has-text("Conseil")',
                                        'a:has-text("Actualités")', 'a:has-text("Publications")'
                                    ];
                                    
                                    selectors.forEach(selector => {
                                        try {
                                            const elements = document.querySelectorAll(selector);
                                            elements.forEach(el => {
                                                const text = el.textContent?.toLowerCase() || '';
                                                const href = el.href;
                                                if (href && (
                                                    text.includes('délibération') || 
                                                    text.includes('conseil') ||
                                                    text.includes('actualité') ||
                                                    text.includes('publication')
                                                )) {
                                                    liens.push({
                                                        text: el.textContent?.trim() || '',
                                                        url: href
                                                    });
                                                }
                                            });
                                        } catch(e) {}
                                    });
                                    
                                    return liens.slice(0, 3); // Max 3 liens par site
                                }
                            ''')
                            
                            print(f"    📋 {len(liens_interessants)} liens trouvés")
                            
                            # Analyser chaque lien
                            for lien in liens_interessants:
                                try:
                                    await page.goto(lien['url'], timeout=15000, wait_until='networkidle')
                                    await page.wait_for_timeout(1500)
                                    
                                    # Extraire contenu texte
                                    contenu = await page.evaluate('() => document.body.innerText || ""')
                                    
                                    # Analyser pour chaufferies
                                    mots_cles, confiance = self.analyser_texte(contenu)
                                    
                                    if mots_cles:
                                        opportunites.append(Opportunite(
                                            commune=commune,
                                            departement=dept,
                                            source='playwright',
                                            date=datetime.now().strftime('%Y-%m-%d'),
                                            titre=lien['text'][:120],
                                            description=contenu[:400],
                                            mots_cles=mots_cles,
                                            url_source=lien['url'],
                                            confiance=confiance,
                                            population=info['pop']
                                        ))
                                        print(f"    ✅ OPPORTUNITÉ: {lien['text'][:50]}... ({confiance})")
                                        
                                except Exception as e:
                                    print(f"    ⚠️ Erreur lien {lien['url']}: {e}")
                                    
                                await page.wait_for_timeout(1000)  # Pause entre pages
                                
                        except Exception as e:
                            print(f"    ❌ Erreur {commune}: {e}")
                            
                        await page.wait_for_timeout(3000)  # Pause entre communes
                        
                await browser.close()
                
        except Exception as e:
            print(f"❌ Erreur Playwright globale: {e}")
            
        print(f"📊 Total Playwright: {len(opportunites)} opportunités\n")
        return opportunites

    def generer_rapport_final(self, toutes_opportunites: List[Opportunite]) -> str:
        """Rapport final détaillé"""
        
        if not toutes_opportunites:
            return "❌ AUCUNE OPPORTUNITÉ DÉTECTÉE - ÉCHEC TOTAL"
            
        # Statistics
        stats_source = {}
        stats_confiance = {'forte': 0, 'moyenne': 0, 'faible': 0}
        stats_departement = {}
        
        for opp in toutes_opportunites:
            stats_source[opp.source] = stats_source.get(opp.source, 0) + 1
            stats_confiance[opp.confiance] += 1
            stats_departement[opp.departement] = stats_departement.get(opp.departement, 0) + 1
            
        rapport = []
        rapport.append("🎯 RAPPORT FINAL - SCRAPER HYBRIDE CHAUFFERIES")
        rapport.append("=" * 70)
        rapport.append(f"📊 STATISTIQUES:")
        rapport.append(f"  • Total opportunités: {len(toutes_opportunites)}")
        rapport.append(f"  • Sources: {dict(stats_source)}")  
        rapport.append(f"  • Confiance: Forte={stats_confiance['forte']}, Moyenne={stats_confiance['moyenne']}")
        rapport.append(f"  • Départements: {dict(stats_departement)}")
        rapport.append("")
        
        # Top opportunités FORTES
        fortes = [o for o in toutes_opportunites if o.confiance == 'forte']
        if fortes:
            rapport.append("🔥 OPPORTUNITÉS PRIORITAIRES (CONFIANCE FORTE)")
            rapport.append("-" * 60)
            for i, opp in enumerate(fortes[:8], 1):
                rapport.append(f"{i}. 📍 {opp.commune} ({opp.departement})")
                rapport.append(f"   📅 {opp.date} | 🔗 {opp.source}")
                rapport.append(f"   📰 {opp.titre}")
                rapport.append(f"   🎯 Mots-clés: {', '.join(opp.mots_cles)}")
                if opp.population:
                    rapport.append(f"   👥 Population: {opp.population:,}")
                rapport.append(f"   🌐 {opp.url_source}")
                rapport.append("")
                
        # Opportunités moyennes  
        moyennes = [o for o in toutes_opportunites if o.confiance == 'moyenne']
        if moyennes:
            rapport.append("⚡ OPPORTUNITÉS SECONDAIRES (CONFIANCE MOYENNE)")
            rapport.append("-" * 50)
            for i, opp in enumerate(moyennes[:5], 1):
                rapport.append(f"{i}. {opp.commune} - {opp.titre[:60]}...")
                rapport.append(f"   🎯 {', '.join(opp.mots_cles)} | 🔗 {opp.source}")
                rapport.append("")
                
        # Recommandations
        rapport.append("💡 RECOMMANDATIONS POUR TON ENTRETIEN:")
        rapport.append("-" * 40)
        if len(toutes_opportunites) >= 5:
            rapport.append("✅ EXCELLENT - Dataset convaincant pour l'entretien")
            rapport.append("📈 Tu as prouvé l'efficacité de l'approche technique")
            rapport.append("🎯 Focus sur les opportunités 'forte confiance'")
        elif len(toutes_opportunites) >= 2:
            rapport.append("👍 BON - Quelques pistes détectées")
            rapport.append("🔧 Affiner les mots-clés pour + de résultats")
        else:
            rapport.append("⚠️ FAIBLE - Peu d'opportunités trouvées")
            rapport.append("🔄 Élargir la recherche ou changer d'approche")
            
        return "\n".join(rapport)

    async def executer_scraping_complet(self) -> List[Opportunite]:
        """Execution complète hybride"""
        print("🚀 DÉMARRAGE SCRAPER HYBRIDE COMPLET")
        print("💡 Stratégie: API data.gouv.fr + Playwright anti-blocage")
        print("🎯 Objectif: Chaufferies biomasse Auvergne")
        print("=" * 70)
        
        start_time = time.time()
        toutes_opportunites = []
        
        # Phase 1: API data.gouv.fr corrigée
        opportunites_api = self.scraper_data_gouv_corrige()
        toutes_opportunites.extend(opportunites_api)
        
        # Phase 2: Playwright si disponible
        if PLAYWRIGHT_AVAILABLE:
            opportunites_playwright = await self.scraper_playwright()
            toutes_opportunites.extend(opportunites_playwright)
        else:
            print("⚠️ Playwright ignoré - installation manquante")
        
        # Dédoublonnage par URL
        urls_vues = set()
        opportunites_uniques = []
        for opp in toutes_opportunites:
            if opp.url_source not in urls_vues:
                urls_vues.add(opp.url_source)
                opportunites_uniques.append(opp)
                
        print(f"⏱️ SCRAPING TERMINÉ EN {time.time() - start_time:.1f}s")
        print(f"📊 {len(opportunites_uniques)} opportunités uniques détectées")
        
        return opportunites_uniques

async def main():
    """Fonction principale"""
    scraper = ScraperHybride()
    
    # Execution
    opportunites = await scraper.executer_scraping_complet()
    
    # Rapport final
    rapport = scraper.generer_rapport_final(opportunites)
    
    print("\n" + "=" * 80)
    print("📋 RAPPORT FINAL")  
    print("=" * 80)
    print(rapport)
    
    # Sauvegarde JSON
    if opportunites:
        filename = f'chaufferies_hybride_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([asdict(opp) for opp in opportunites], f, ensure_ascii=False, indent=2)
        print(f"\n💾 Données sauvegardées: {filename}")
        
        # Export CSV pour analyse
        csv_filename = f'chaufferies_hybride_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
        with open(csv_filename, 'w', encoding='utf-8') as f:
            f.write("Commune,Departement,Source,Date,Titre,Mots_cles,URL,Confiance,Population\n")
            for opp in opportunites:
                f.write(f'"{opp.commune}","{opp.departement}","{opp.source}","{opp.date}","{opp.titre}","{"; ".join(opp.mots_cles)}","{opp.url_source}","{opp.confiance}","{opp.population or ""}"\n')
        print(f"📊 Export CSV: {csv_filename}")

if __name__ == "__main__":
    asyncio.run(main())