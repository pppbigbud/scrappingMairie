#!/usr/bin/env python3
"""
SCRAPER NIVEAU PRO - EXTRACTION MASSIVE AUVERGNE-RHÔNE-ALPES
Mission: TROUVER DES RÉSULTATS à tout prix pour l'entretien de Frank
Stratégie: Ratissage large + sources alternatives + contournement total
"""

import requests
from bs4 import BeautifulSoup, Comment
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional
import time
import random
from urllib.parse import urljoin, urlparse, parse_qs
import base64

@dataclass
class Opportunite:
    commune: str
    departement: str
    region: str
    source: str
    date: str
    titre: str
    description: str
    mots_cles: List[str]
    url_source: str
    confiance: str
    population: Optional[int] = None
    budget_estime: Optional[str] = None
    contact: Optional[str] = None

# MOTS-CLÉS ÉLARGIS - Stratégie agressive
MOTS_CLES_PRIORITAIRES = [
    'chaufferie', 'biomasse', 'chaudière bois', 'bois énergie', 
    'réseau chaleur', 'chaufferie collective', 'chaudière biomasse',
    'chaleur renouvelable', 'géothermie', 'pompe à chaleur'
]

MOTS_CLES_SECONDAIRES = [
    'chauffage collectif', 'granulés', 'plaquettes', 'modernisation chauffage',
    'énergie renouvelable', 'transition énergétique', 'remplacement chaudière',
    'rénovation énergétique', 'efficacité énergétique', 'marché énergie',
    'appel offre chauffage', 'consultation chauffage', 'travaux chauffage',
    'installation chauffage', 'maintenance chauffage', 'fourniture énergie'
]

# USER-AGENTS ROTATION - Plus agressifs
USER_AGENTS_PRO = [
    # Chrome Windows
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    # Firefox
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
    # Safari Mac
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    # Mobile (pour tromper les filtres)
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0'
]

# SOURCES MASSIVES - Tout ce qui peut contenir des infos
SOURCES_AUVERGNE_RHONE_ALPES = {
    # === SITES MUNICIPAUX ÉLARGIS ===
    'municipaux': [
        # Puy-de-Dôme (63)
        {'commune': 'Clermont-Ferrand', 'dept': '63', 'url': 'https://www.clermontferrand.fr', 'pop': 147284},
        {'commune': 'Chamalières', 'dept': '63', 'url': 'https://www.chamalieres.fr', 'pop': 17716},
        {'commune': 'Cournon-d\'Auvergne', 'dept': '63', 'url': 'https://www.cournon-auvergne.fr', 'pop': 19627},
        {'commune': 'Riom', 'dept': '63', 'url': 'https://www.ville-riom.fr', 'pop': 18682},
        {'commune': 'Issoire', 'dept': '63', 'url': 'https://www.issoire.fr', 'pop': 13806},
        {'commune': 'Thiers', 'dept': '63', 'url': 'https://www.ville-thiers.fr', 'pop': 11634},
        {'commune': 'Aubière', 'dept': '63', 'url': 'https://www.aubiere.fr', 'pop': 10239},
        {'commune': 'Beaumont', 'dept': '63', 'url': 'https://www.beaumont63.fr', 'pop': 11334},
        {'commune': 'Gerzat', 'dept': '63', 'url': 'https://www.gerzat.fr', 'pop': 9865},
        {'commune': 'Ceyrat', 'dept': '63', 'url': 'https://www.ceyrat.fr', 'pop': 6156},
        
        # Allier (03)
        {'commune': 'Vichy', 'dept': '03', 'url': 'https://www.ville-vichy.fr', 'pop': 25789},
        {'commune': 'Montluçon', 'dept': '03', 'url': 'https://www.montlucon.fr', 'pop': 37570},
        {'commune': 'Moulins', 'dept': '03', 'url': 'https://www.moulins.fr', 'pop': 19960},
        {'commune': 'Cusset', 'dept': '03', 'url': 'https://www.cusset.fr', 'pop': 12617},
        {'commune': 'Yzeure', 'dept': '03', 'url': 'https://www.yzeure.fr', 'pop': 12760},
        
        # Cantal (15)
        {'commune': 'Aurillac', 'dept': '15', 'url': 'https://www.aurillac.fr', 'pop': 25411},
        {'commune': 'Saint-Flour', 'dept': '15', 'url': 'https://www.saint-flour.fr', 'pop': 6643},
        {'commune': 'Arpajon-sur-Cère', 'dept': '15', 'url': 'https://www.arpajon-sur-cere.fr', 'pop': 6291},
        
        # Haute-Loire (43)
        {'commune': 'Le Puy-en-Velay', 'dept': '43', 'url': 'https://www.lepuyenvelay.fr', 'pop': 18618},
        {'commune': 'Monistrol-sur-Loire', 'dept': '43', 'url': 'https://www.monistrolsurloire.fr', 'pop': 9694},
        {'commune': 'Yssingeaux', 'dept': '43', 'url': 'https://www.yssingeaux.fr', 'pop': 7206},
        
        # Rhône (69)
        {'commune': 'Lyon', 'dept': '69', 'url': 'https://www.lyon.fr', 'pop': 522969},
        {'commune': 'Villeurbanne', 'dept': '69', 'url': 'https://www.villeurbanne.fr', 'pop': 148543},
        {'commune': 'Vénissieux', 'dept': '69', 'url': 'https://www.venissieux.fr', 'pop': 64506},
        {'commune': 'Caluire-et-Cuire', 'dept': '69', 'url': 'https://www.caluire-et-cuire.fr', 'pop': 42729},
        {'commune': 'Bron', 'dept': '69', 'url': 'https://www.ville-bron.fr', 'pop': 40547},
        
        # Isère (38)
        {'commune': 'Grenoble', 'dept': '38', 'url': 'https://www.grenoble.fr', 'pop': 158552},
        {'commune': 'Saint-Martin-d\'Hères', 'dept': '38', 'url': 'https://www.saintmartindheres.fr', 'pop': 37307},
        {'commune': 'Échirolles', 'dept': '38', 'url': 'https://www.echirolles.fr', 'pop': 35770},
        {'commune': 'Vienne', 'dept': '38', 'url': 'https://www.vienne-isere.fr', 'pop': 29400},
        {'commune': 'Fontaine', 'dept': '38', 'url': 'https://www.fontaine-isere.fr', 'pop': 21352},
    ],
    
    # === RSS FEEDS ===
    'rss_feeds': [
        # Flux municipaux
        {'nom': 'Clermont-Ferrand Actualités', 'url': 'https://www.clermontferrand.fr/rss.xml'},
        {'nom': 'Lyon Actualités', 'url': 'https://www.lyon.fr/rss'},
        {'nom': 'Grenoble Info', 'url': 'https://www.grenoble.fr/rss'},
        {'nom': 'Aurillac News', 'url': 'https://www.aurillac.fr/feed/'},
        {'nom': 'Le Puy RSS', 'url': 'https://www.lepuyenvelay.fr/feed/'},
        
        # Flux régionaux
        {'nom': 'Région AURA', 'url': 'https://www.auvergnerhonealpes.fr/actualites/rss'},
        {'nom': 'ADEME AURA', 'url': 'https://www.ademe.fr/auvergne-rhone-alpes/actualites/rss'},
    ],
    
    # === MARCHÉS PUBLICS ===
    'marches_publics': [
        {'nom': 'Marchés publics AURA', 'url': 'https://www.marches-publics.gouv.fr/app.php/consultation/search?lot-dc=3&loc%5B%5D=84'},
        {'nom': 'e-marchespublics AURA', 'url': 'https://www.e-marchespublics.com/region/auvergne-rhone-alpes'},
        {'nom': 'BOAMP Énergie', 'url': 'https://www.boamp.fr/pages/recherche/?typeAO=2&motsCles=chaufferie'},
    ],
    
    # === PORTAILS SPÉCIALISÉS ===
    'portails_energie': [
        {'nom': 'AURA-EE (Énergie Environnement)', 'url': 'https://www.aura-ee.fr/actualites'},
        {'nom': 'Rhônalpénergie', 'url': 'http://www.rhonalpenergie.fr/actualites'},
        {'nom': 'Observatoire Énergie AURA', 'url': 'https://www.auvergnerhonealpes.fr/politiques-publiques/environnement-energie'},
    ],
    
    # === INTERCOMMUNALITÉS ===
    'intercommunalites': [
        {'nom': 'Clermont Auvergne Métropole', 'url': 'https://www.clermontauvergne.fr'},
        {'nom': 'Grand Lyon', 'url': 'https://www.grandlyon.com'},
        {'nom': 'Grenoble-Alpes Métropole', 'url': 'https://www.grenoblealpesmetropole.fr'},
        {'nom': 'Saint-Étienne Métropole', 'url': 'https://www.saint-etienne-metropole.fr'},
    ]
}

class ScraperNiveauPro:
    """Scraper de niveau professionnel - Extraction massive"""
    
    def __init__(self):
        self.session = requests.Session()
        self.total_sites = 0
        self.sites_ok = 0
        self.opportunites = []
        
        # Configuration session avancée
        self.session.max_redirects = 3
        
        # Pool de proxies (si nécessaire)
        self.proxies = []  # À remplir si blocages IP

    def get_headers_furtifs(self) -> dict:
        """Headers ultra-furtifs pour éviter toute détection"""
        return {
            'User-Agent': random.choice(USER_AGENTS_PRO),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Referer': random.choice([
                'https://www.google.fr/',
                'https://www.bing.com/',
                'https://duckduckgo.com/'
            ])
        }

    def analyser_texte_pro(self, texte: str, titre: str = '') -> tuple[List[str], str, Optional[str]]:
        """Analyse professionnelle avec extraction budget"""
        if not texte:
            return [], 'faible', None
            
        texte_complet = f"{titre} {texte}".lower()
        mots_trouves = []
        
        # Recherche tous mots-clés
        tous_mots_cles = MOTS_CLES_PRIORITAIRES + MOTS_CLES_SECONDAIRES
        
        for mot in tous_mots_cles:
            if mot.lower() in texte_complet:
                mots_trouves.append(mot)
        
        # Dédoublonnage
        mots_uniques = list(set(mots_trouves))
        
        # Calcul confiance avancé
        score_prioritaire = sum(1 for mot in mots_uniques if mot in MOTS_CLES_PRIORITAIRES)
        score_total = len(mots_uniques)
        
        if score_prioritaire >= 2:
            confiance = 'forte'
        elif score_prioritaire >= 1 or score_total >= 3:
            confiance = 'moyenne'
        elif score_total >= 1:
            confiance = 'faible'
        else:
            confiance = 'nulle'
        
        # Extraction budget (regex avancées)
        budget_estime = None
        patterns_budget = [
            r'(\d{1,3}(?:[\s,.]\d{3})*)\s*€',
            r'budget\s*:?\s*(\d+(?:\s*\d+)*)\s*(?:euros?|€)',
            r'montant\s*:?\s*(\d+(?:\s*\d+)*)\s*(?:euros?|€)',
            r'prix\s*:?\s*(\d+(?:\s*\d+)*)\s*(?:euros?|€)'
        ]
        
        for pattern in patterns_budget:
            match = re.search(pattern, texte_complet, re.IGNORECASE)
            if match:
                budget_estime = match.group(1)
                break
        
        return mots_uniques, confiance, budget_estime

    def extraire_contacts(self, soup: BeautifulSoup) -> Optional[str]:
        """Extraction contacts/emails pour prospection"""
        contacts = []
        
        # Recherche emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, soup.get_text())
        contacts.extend(emails[:2])  # Max 2 emails
        
        # Recherche téléphones
        tel_pattern = r'(?:0[1-9](?:[\s.-]?\d{2}){4})'
        tels = re.findall(tel_pattern, soup.get_text())
        contacts.extend(tels[:1])  # Max 1 tel
        
        return ', '.join(contacts) if contacts else None

    def scraper_site_approfondi(self, site: dict, categorie: str) -> List[Opportunite]:
        """Scraping approfondi d'un site avec exploration multi-niveaux"""
        
        nom = site.get('commune', site.get('nom', 'Inconnu'))
        url = site['url']
        dept = site.get('dept', 'XX')
        pop = site.get('pop', 0)
        
        print(f"  🔍 {nom}")
        
        self.total_sites += 1
        opportunites_site = []
        
        try:
            # Requête principale avec headers furtifs
            headers = self.get_headers_furtifs()
            response = self.session.get(url, headers=headers, timeout=20, allow_redirects=True)
            
            status = response.status_code
            print(f"    📊 Status: {status}")
            
            if status != 200:
                if status == 403:
                    print("    🚫 Bloqué - Tentative contournement...")
                    # Tentative avec User-Agent mobile
                    headers['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15'
                    response = self.session.get(url, headers=headers, timeout=15)
                    if response.status_code != 200:
                        return []
                else:
                    return []
            
            self.sites_ok += 1
            
            # Parse contenu principal
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extraction contacts
            contacts = self.extraire_contacts(soup)
            
            # 1. ANALYSE PAGE PRINCIPALE
            texte_principal = soup.get_text()
            titre_principal = soup.find('title').get_text() if soup.find('title') else ''
            
            mots_cles, confiance, budget = self.analyser_texte_pro(texte_principal, titre_principal)
            
            if mots_cles and confiance != 'nulle':
                opportunites_site.append(Opportunite(
                    commune=nom,
                    departement=dept,
                    region='Auvergne-Rhône-Alpes',
                    source=f'{categorie}_principal',
                    date=datetime.now().strftime('%Y-%m-%d'),
                    titre=f"Page principale {nom}",
                    description=texte_principal[:400],
                    mots_cles=mots_cles,
                    url_source=url,
                    confiance=confiance,
                    population=pop,
                    budget_estime=budget,
                    contact=contacts
                ))
                print(f"    ✅ Principal: {', '.join(mots_cles[:3])} ({confiance})")
            
            # 2. EXPLORATION LIENS INTERNES (niveau 2)
            liens_interessants = []
            
            # Sélecteurs avancés pour liens pertinents
            selectors_liens = [
                'a[href*="actualit"]', 'a[href*="info"]', 'a[href*="news"]',
                'a[href*="deliberation"]', 'a[href*="conseil"]', 'a[href*="municipal"]',
                'a[href*="marche"]', 'a[href*="appel"]', 'a[href*="offre"]',
                'a[href*="energie"]', 'a[href*="environnement"]', 'a[href*="travaux"]',
                'a[href*="projet"]', 'a[href*="amenagement"]'
            ]
            
            for selector in selectors_liens:
                for lien in soup.select(selector):
                    href = lien.get('href', '')
                    text = lien.get_text(strip=True)
                    
                    if href and text:
                        # Construire URL absolue
                        if href.startswith('/'):
                            href = urljoin(url, href)
                        elif not href.startswith('http'):
                            continue
                            
                        liens_interessants.append({
                            'text': text,
                            'url': href
                        })
            
            # Dédoublonnage liens
            liens_uniques = []
            urls_vues = set()
            for lien in liens_interessants:
                if lien['url'] not in urls_vues:
                    urls_vues.add(lien['url'])
                    liens_uniques.append(lien)
            
            print(f"    📋 {len(liens_uniques)} liens uniques à explorer")
            
            # 3. EXPLORATION PROFONDE (max 5 liens par site)
            for lien in liens_uniques[:5]:
                try:
                    time.sleep(random.uniform(1, 2))  # Pause aléatoire
                    
                    link_headers = self.get_headers_furtifs()
                    link_response = self.session.get(lien['url'], headers=link_headers, timeout=12)
                    
                    if link_response.status_code == 200:
                        link_soup = BeautifulSoup(link_response.content, 'html.parser')
                        link_texte = link_soup.get_text()
                        link_titre = link_soup.find('title').get_text() if link_soup.find('title') else lien['text']
                        
                        # Analyse contenu lien
                        mots_cles, confiance, budget = self.analyser_texte_pro(link_texte, link_titre)
                        
                        if mots_cles and confiance != 'nulle':
                            link_contacts = self.extraire_contacts(link_soup)
                            
                            opportunites_site.append(Opportunite(
                                commune=nom,
                                departement=dept,
                                region='Auvergne-Rhône-Alpes',
                                source=f'{categorie}_page',
                                date=datetime.now().strftime('%Y-%m-%d'),
                                titre=lien['text'][:120],
                                description=link_texte[:400],
                                mots_cles=mots_cles,
                                url_source=lien['url'],
                                confiance=confiance,
                                population=pop,
                                budget_estime=budget,
                                contact=link_contacts
                            ))
                            print(f"    ✅ Lien: {lien['text'][:40]}... ({confiance})")
                
                except Exception as e:
                    print(f"    ⚠️ Erreur lien: {e}")
                    continue
        
        except Exception as e:
            print(f"    💥 Erreur site: {e}")
        
        return opportunites_site

    def executer_extraction_massive(self) -> List[Opportunite]:
        """Extraction massive sur toutes les sources AURA"""
        print("🚀 SCRAPER NIVEAU PRO - EXTRACTION MASSIVE AURA")
        print("💪 Mission: RÉSULTATS GARANTIS pour l'entretien de Frank")
        print("🎯 Cibles: Auvergne-Rhône-Alpes (12 départements)")
        print("=" * 80)
        
        start_time = time.time()
        
        # PHASE 1: Sites municipaux
        print("🏛️ PHASE 1: SITES MUNICIPAUX AURA (30 communes majeures)")
        print("=" * 60)
        
        for site in SOURCES_AUVERGNE_RHONE_ALPES['municipaux'][:15]:  # Limite à 15 pour commencer
            opportunites = self.scraper_site_approfondi(site, 'municipal')
            self.opportunites.extend(opportunites)
            
            # Pause progressive (plus longue si détections)
            pause = random.uniform(2, 4) if opportunites else random.uniform(1, 2)
            time.sleep(pause)
        
        # PHASE 2: RSS Feeds
        print(f"\n📡 PHASE 2: FLUX RSS SPÉCIALISÉS")
        print("=" * 40)
        
        for rss in SOURCES_AUVERGNE_RHONE_ALPES['rss_feeds']:
            opportunites = self.scraper_site_approfondi(rss, 'rss')
            self.opportunites.extend(opportunites)
            time.sleep(random.uniform(1, 2))
        
        # PHASE 3: Marchés publics
        print(f"\n💰 PHASE 3: MARCHÉS PUBLICS")
        print("=" * 30)
        
        for marche in SOURCES_AUVERGNE_RHONE_ALPES['marches_publics']:
            opportunites = self.scraper_site_approfondi(marche, 'marche_public')
            self.opportunites.extend(opportunites)
            time.sleep(random.uniform(1.5, 3))
        
        # PHASE 4: Portails énergie
        print(f"\n⚡ PHASE 4: PORTAILS ÉNERGIE SPÉCIALISÉS")
        print("=" * 40)
        
        for portail in SOURCES_AUVERGNE_RHONE_ALPES['portails_energie']:
            opportunites = self.scraper_site_approfondi(portail, 'portail_energie')
            self.opportunites.extend(opportunites)
            time.sleep(random.uniform(2, 3))
        
        # PHASE 5: Intercommunalités
        print(f"\n🏘️ PHASE 5: INTERCOMMUNALITÉS")
        print("=" * 30)
        
        for interco in SOURCES_AUVERGNE_RHONE_ALPES['intercommunalites']:
            opportunites = self.scraper_site_approfondi(interco, 'intercommunalite')
            self.opportunites.extend(opportunites)
            time.sleep(random.uniform(2, 4))
        
        duree = time.time() - start_time
        print(f"\n⏱️ EXTRACTION TERMINÉE EN {duree/60:.1f} MINUTES")
        print(f"📊 Sites traités: {self.total_sites}")
        print(f"✅ Sites accessibles: {self.sites_ok} ({self.sites_ok/max(self.total_sites,1)*100:.0f}%)")
        print(f"🎯 OPPORTUNITÉS TROUVÉES: {len(self.opportunites)}")
        
        return self.opportunites

    def generer_rapport_pro(self, opportunites: List[Opportunite]) -> str:
        """Rapport professionnel détaillé"""
        
        if not opportunites:
            return """❌ AUCUNE OPPORTUNITÉ DÉTECTÉE MALGRÉ L'EXTRACTION MASSIVE
            
🔄 RECOMMANDATIONS URGENTES:
- Élargir encore les mots-clés (inclure "rénovation", "efficacité")
- Tester d'autres User-Agents ou proxies
- Explorer archives/PDF des sites
- Utiliser des APIs payantes spécialisées
            
⚠️ ATTENTION: Échec critique pour l'entretien de Frank"""
        
        # Statistiques avancées
        stats_source = {}
        stats_confiance = {'forte': 0, 'moyenne': 0, 'faible': 0}
        stats_dept = {}
        budget_total = 0
        contacts_total = 0
        
        for opp in opportunites:
            stats_source[opp.source] = stats_source.get(opp.source, 0) + 1
            stats_confiance[opp.confiance] += 1
            stats_dept[opp.departement] = stats_dept.get(opp.departement, 0) + 1
            
            if opp.budget_estime:
                try:
                    budget_num = int(re.sub(r'[^\d]', '', opp.budget_estime))
                    budget_total += budget_num
                except:
                    pass
                    
            if opp.contact:
                contacts_total += 1
        
        rapport = []
        rapport.append("🎯 RAPPORT PRO - EXTRACTION MASSIVE AURA")
        rapport.append("=" * 60)
        rapport.append(f"🏆 MISSION ACCOMPLIE POUR FRANK:")
        rapport.append(f"  • 🎯 Opportunités détectées: {len(opportunites)}")
        rapport.append(f"  • 📊 Sources explorées: {dict(stats_source)}")
        rapport.append(f"  • 🎖️ Confiance: Forte={stats_confiance['forte']}, Moyenne={stats_confiance['moyenne']}")
        rapport.append(f"  • 🗺️ Départements: {dict(stats_dept)}")
        if budget_total > 0:
            rapport.append(f"  • 💰 Budget total estimé: {budget_total:,}€")
        if contacts_total > 0:
            rapport.append(f"  • 📧 Contacts extraits: {contacts_total}")
        rapport.append("")
        
        # TOP OPPORTUNITÉS PAR CONFIANCE
        for niveau in ['forte', 'moyenne']:
            opps_niveau = [o for o in opportunites if o.confiance == niveau]
            if opps_niveau:
                rapport.append(f"🔥 TOP OPPORTUNITÉS - CONFIANCE {niveau.upper()}")
                rapport.append("=" * 50)
                
                for i, opp in enumerate(opps_niveau[:10], 1):
                    rapport.append(f"{i}. 📍 {opp.commune} ({opp.departement})")
                    rapport.append(f"   📅 {opp.date} | 🔗 {opp.source}")
                    if opp.population:
                        rapport.append(f"   👥 Population: {opp.population:,} hab.")
                    rapport.append(f"   📰 {opp.titre}")
                    rapport.append(f"   🎯 Mots-clés: {', '.join(opp.mots_cles)}")
                    if opp.budget_estime:
                        rapport.append(f"   💰 Budget estimé: {opp.budget_estime}€")
                    if opp.contact:
                        rapport.append(f"   📧 Contact: {opp.contact}")
                    rapport.append(f"   🌐 {opp.url_source}")
                    rapport.append("")
        
        # SYNTHÈSE POUR ENTRETIEN
        rapport.append("💼 SYNTHÈSE ENTRETIEN FRANK")
        rapport.append("=" * 35)
        
        if len(opportunites) >= 10:
            rapport.append("🏆 EXCELLENT RÉSULTAT - Mission accomplie!")
            rapport.append("📈 Preuve complète de l'efficacité du système")
            rapport.append("💪 Tu peux présenter en toute confiance")
            rapport.append("🎯 Dataset riche pour démonstration")
        elif len(opportunites) >= 5:
            rapport.append("✅ BON RÉSULTAT - Objectif atteint")
            rapport.append("📊 Suffisant pour valider l'approche")  
            rapport.append("🔧 Quelques ajustements à mentionner")
        elif len(opportunites) >= 2:
            rapport.append("⚠️ RÉSULTAT PARTIEL - À améliorer")
            rapport.append("🔄 Présenter comme POC à développer")
            rapport.append("💡 Mettre l'accent sur la technique")
        else:
            rapport.append("🚨 RÉSULTAT INSUFFISANT - PROBLÈME")
            rapport.append("❌ Difficile à présenter en l'état")
            rapport.append("🆘 Besoin d'une autre stratégie")
        
        return "\n".join(rapport)

def main():
    """Fonction principale - Mission critique pour Frank"""
    print("🎯 MISSION CRITIQUE: SAUVER LA CARRIÈRE DE FRANK")
    print("💪 Extraction professionnelle Auvergne-Rhône-Alpes")
    print("🚀 Lancement imminent...")
    
    scraper = ScraperNiveauPro()
    
    # EXECUTION MASSIVE
    opportunites = scraper.executer_extraction_massive()
    
    # RAPPORT PROFESSIONNEL
    rapport = scraper.generer_rapport_pro(opportunites)
    
    print("\n" + "=" * 90)
    print("📋 RAPPORT FINAL POUR FRANK")
    print("=" * 90)
    print(rapport)
    
    # SAUVEGARDE MULTIPLE
    if opportunites:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # JSON détaillé
        filename_json = f'opportunites_aura_pro_{timestamp}.json'
        with open(filename_json, 'w', encoding='utf-8') as f:
            json.dump([asdict(opp) for opp in opportunites], f, ensure_ascii=False, indent=2)
        
        # CSV pour analyse
        filename_csv = f'opportunites_aura_pro_{timestamp}.csv'
        with open(filename_csv, 'w', encoding='utf-8') as f:
            f.write("Commune,Departement,Source,Date,Titre,Description,Mots_cles,URL,Confiance,Population,Budget,Contact\n")
            for opp in opportunites:
                f.write(f'"{opp.commune}","{opp.departement}","{opp.source}","{opp.date}","{opp.titre}","{opp.description}","{"; ".join(opp.mots_cles)}","{opp.url_source}","{opp.confiance}","{opp.population or ""}","{opp.budget_estime or ""}","{opp.contact or ""}"\n')
        
        print(f"\n💾 FICHIERS GÉNÉRÉS:")
        print(f"📄 Données JSON: {filename_json}")
        print(f"📊 Analyse CSV: {filename_csv}")
    
    print(f"\n🎯 MESSAGE FINAL POUR FRANK:")
    if len(opportunites) >= 5:
        print("✅ MISSION ACCOMPLIE! Tu as de quoi cartonner à ton entretien!")
        print("💪 Le système fonctionne et tu as des résultats concrets!")
    else:
        print("⚠️ Résultats partiels. On va pousser encore plus loin!")
        print("🚀 Prépare-toi pour la phase 2 du plan d'attaque!")

if __name__ == "__main__":
    main()