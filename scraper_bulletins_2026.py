#!/usr/bin/env python3
"""
SCRAPER BULLETINS MUNICIPAUX 2026 - VERSION AMÉLIORÉE
Cible : Les bulletins municipaux où se trouvent les vraies infos projets
Inspiré du succès Nivigne et Suran
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
from urllib.parse import urljoin, urlparse
import sys

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

@dataclass
class ProjetChaufferie:
    commune: str
    departement: str
    source_type: str  # 'bulletin', 'deliberation', 'actualite'
    date_publication: str
    titre: str
    extrait: str  # Le passage pertinent
    mots_cles_trouves: List[str]
    phase_estimee: str  # 'reflexion', 'etude', 'projet', 'en_cours'
    url_source: str
    contact_mairie: Optional[str] = None
    population: Optional[int] = None

# MOTS-CLÉS CHAUFFERIE (prioritaires)
MOTS_CLES_CHAUFFERIE = [
    'chaufferie', 'chaudière', 'chauffage',
    'biomasse', 'bois énergie', 'bois-énergie',
    'granulés', 'plaquettes', 'pellets',
    'fioul', 'fuel', 'remplacement chauffage',
    'réseau de chaleur', 'réseau chaleur'
]

# MOTS-CLÉS CONTEXTE (confirment un projet)
MOTS_CLES_CONTEXTE = [
    'projet', 'étude', 'réflexion', 'programmation',
    'remplacement', 'modernisation', 'rénovation',
    'transition énergétique', 'plan climat',
    'subvention', 'financement', 'budget',
    'mandat', 'mandature', 'conseil municipal'
]

# URLs PATTERNS pour trouver les bulletins
BULLETIN_PATTERNS = [
    '/bulletin', '/bulletins', '/bulletin-municipal',
    '/publications', '/magazine', '/journal',
    '/vie-municipale', '/actualites', '/infos-pratiques',
    '/mairie/publications', '/communication'
]

# User agents réalistes
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

# COMMUNES AURA - Focus petites/moyennes (plus de chances d'avoir bulletins accessibles)
COMMUNES_AURA = [
    # Ain (01) - Comme Nivigne et Suran !
    {'commune': 'Nivigne-et-Suran', 'dept': '01', 'url': 'https://www.nivigne-et-suran.fr', 'pop': 2500},
    {'commune': 'Oyonnax', 'dept': '01', 'url': 'https://www.oyonnax.fr', 'pop': 22500},
    {'commune': 'Bourg-en-Bresse', 'dept': '01', 'url': 'https://www.bourgenbresse.fr', 'pop': 41000},
    {'commune': 'Ambérieu-en-Bugey', 'dept': '01', 'url': 'https://www.amberieu-en-bugey.fr', 'pop': 14000},
    {'commune': 'Belley', 'dept': '01', 'url': 'https://www.belley.fr', 'pop': 9000},
    {'commune': 'Ferney-Voltaire', 'dept': '01', 'url': 'https://www.ferney-voltaire.fr', 'pop': 10000},
    {'commune': 'Miribel', 'dept': '01', 'url': 'https://www.miribel.fr', 'pop': 10000},
    {'commune': 'Villars-les-Dombes', 'dept': '01', 'url': 'https://www.villars-les-dombes.fr', 'pop': 4500},
    {'commune': 'Châtillon-sur-Chalaronne', 'dept': '01', 'url': 'https://www.chatillon-sur-chalaronne.fr', 'pop': 5000},
    {'commune': 'Trévoux', 'dept': '01', 'url': 'https://www.mairie-trevoux.fr', 'pop': 7000},
    
    # Haute-Savoie (74) - Communes forestières
    {'commune': 'Annecy', 'dept': '74', 'url': 'https://www.annecy.fr', 'pop': 130000},
    {'commune': 'Thonon-les-Bains', 'dept': '74', 'url': 'https://www.ville-thonon.fr', 'pop': 35000},
    {'commune': 'Annemasse', 'dept': '74', 'url': 'https://www.annemasse.fr', 'pop': 36000},
    {'commune': 'Cluses', 'dept': '74', 'url': 'https://www.cluses.fr', 'pop': 18000},
    {'commune': 'Sallanches', 'dept': '74', 'url': 'https://www.sallanches.fr', 'pop': 16000},
    {'commune': 'Bonneville', 'dept': '74', 'url': 'https://www.bonneville.fr', 'pop': 13000},
    {'commune': 'La Roche-sur-Foron', 'dept': '74', 'url': 'https://www.larochesurforon.fr', 'pop': 12000},
    {'commune': 'Rumilly', 'dept': '74', 'url': 'https://www.ville-rumilly74.fr', 'pop': 15000},
    
    # Savoie (73) - Zone montagne = biomasse
    {'commune': 'Chambéry', 'dept': '73', 'url': 'https://www.chambery.fr', 'pop': 60000},
    {'commune': 'Aix-les-Bains', 'dept': '73', 'url': 'https://www.aixlesbains.fr', 'pop': 31000},
    {'commune': 'Albertville', 'dept': '73', 'url': 'https://www.albertville.fr', 'pop': 19000},
    {'commune': 'La Motte-Servolex', 'dept': '73', 'url': 'https://www.lamotteservolex.fr', 'pop': 12000},
    {'commune': 'Saint-Jean-de-Maurienne', 'dept': '73', 'url': 'https://www.saintjeandemaurienne.fr', 'pop': 8000},
    {'commune': 'Bourg-Saint-Maurice', 'dept': '73', 'url': 'https://www.bourgsaintmaurice.fr', 'pop': 7000},
    
    # Isère (38)
    {'commune': 'Voiron', 'dept': '38', 'url': 'https://www.ville-voiron.fr', 'pop': 21000},
    {'commune': 'Vienne', 'dept': '38', 'url': 'https://www.vienne.fr', 'pop': 30000},
    {'commune': 'Bourgoin-Jallieu', 'dept': '38', 'url': 'https://www.bourgoinjallieu.fr', 'pop': 28000},
    {'commune': 'Villefontaine', 'dept': '38', 'url': 'https://www.villefontaine.fr', 'pop': 19000},
    {'commune': 'L\'Isle-d\'Abeau', 'dept': '38', 'url': 'https://www.isle-dabeau.fr', 'pop': 16000},
    {'commune': 'Pontcharra', 'dept': '38', 'url': 'https://www.pontcharra.fr', 'pop': 7500},
    
    # Drôme (26)
    {'commune': 'Valence', 'dept': '26', 'url': 'https://www.valence.fr', 'pop': 65000},
    {'commune': 'Montélimar', 'dept': '26', 'url': 'https://www.montelimar.fr', 'pop': 40000},
    {'commune': 'Romans-sur-Isère', 'dept': '26', 'url': 'https://www.ville-romans.fr', 'pop': 34000},
    {'commune': 'Bourg-lès-Valence', 'dept': '26', 'url': 'https://www.bourg-les-valence.fr', 'pop': 20000},
    {'commune': 'Pierrelatte', 'dept': '26', 'url': 'https://www.pierrelatte.fr', 'pop': 14000},
    
    # Ardèche (07) - Rural forestier
    {'commune': 'Annonay', 'dept': '07', 'url': 'https://www.annonay.fr', 'pop': 17000},
    {'commune': 'Aubenas', 'dept': '07', 'url': 'https://www.aubenas.fr', 'pop': 13000},
    {'commune': 'Guilherand-Granges', 'dept': '07', 'url': 'https://www.guilherandgranges.fr', 'pop': 11500},
    {'commune': 'Tournon-sur-Rhône', 'dept': '07', 'url': 'https://www.tournon-sur-rhone.fr', 'pop': 11000},
    {'commune': 'Privas', 'dept': '07', 'url': 'https://www.privas.fr', 'pop': 8500},
    
    # Loire (42)
    {'commune': 'Saint-Étienne', 'dept': '42', 'url': 'https://www.saint-etienne.fr', 'pop': 175000},
    {'commune': 'Roanne', 'dept': '42', 'url': 'https://www.roanne.fr', 'pop': 35000},
    {'commune': 'Saint-Chamond', 'dept': '42', 'url': 'https://www.saint-chamond.fr', 'pop': 35000},
    {'commune': 'Firminy', 'dept': '42', 'url': 'https://www.ville-firminy.fr', 'pop': 17000},
    {'commune': 'Montbrison', 'dept': '42', 'url': 'https://www.ville-montbrison.fr', 'pop': 16000},
    
    # Puy-de-Dôme (63)
    {'commune': 'Clermont-Ferrand', 'dept': '63', 'url': 'https://www.clermontferrand.fr', 'pop': 147000},
    {'commune': 'Riom', 'dept': '63', 'url': 'https://www.ville-riom.fr', 'pop': 19000},
    {'commune': 'Issoire', 'dept': '63', 'url': 'https://www.issoire.fr', 'pop': 14000},
    {'commune': 'Thiers', 'dept': '63', 'url': 'https://www.ville-thiers.fr', 'pop': 12000},
    {'commune': 'Cournon-d\'Auvergne', 'dept': '63', 'url': 'https://www.cournon-auvergne.fr', 'pop': 20000},
    {'commune': 'Chamalières', 'dept': '63', 'url': 'https://www.ville-chamalieres.fr', 'pop': 18000},
    
    # Allier (03)
    {'commune': 'Vichy', 'dept': '03', 'url': 'https://www.ville-vichy.fr', 'pop': 26000},
    {'commune': 'Montluçon', 'dept': '03', 'url': 'https://www.ville-montlucon.fr', 'pop': 38000},
    {'commune': 'Moulins', 'dept': '03', 'url': 'https://www.moulins.fr', 'pop': 20000},
    {'commune': 'Cusset', 'dept': '03', 'url': 'https://www.ville-cusset.com', 'pop': 14000},
    
    # Cantal (15)
    {'commune': 'Aurillac', 'dept': '15', 'url': 'https://www.aurillac.fr', 'pop': 26000},
    {'commune': 'Saint-Flour', 'dept': '15', 'url': 'https://www.saint-flour.fr', 'pop': 6600},
    {'commune': 'Mauriac', 'dept': '15', 'url': 'https://www.mauriac.fr', 'pop': 3800},
    
    # Haute-Loire (43)
    {'commune': 'Le Puy-en-Velay', 'dept': '43', 'url': 'https://www.lepuyenvelay.fr', 'pop': 19000},
    {'commune': 'Monistrol-sur-Loire', 'dept': '43', 'url': 'https://www.monistrol-sur-loire.fr', 'pop': 9000},
    {'commune': 'Yssingeaux', 'dept': '43', 'url': 'https://www.yssingeaux.fr', 'pop': 7000},
    {'commune': 'Brioude', 'dept': '43', 'url': 'https://www.brioude.fr', 'pop': 6700},
]

class ScraperBulletins2026:
    def __init__(self):
        self.session = requests.Session()
        self.projets_trouves: List[ProjetChaufferie] = []
        self.stats = {
            'communes_scannees': 0,
            'bulletins_trouves': 0,
            'projets_detectes': 0,
            'erreurs': 0
        }
    
    def get_headers(self) -> Dict:
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def fetch_page(self, url: str, timeout: int = 15) -> Optional[BeautifulSoup]:
        """Récupère une page avec gestion d'erreurs"""
        try:
            response = self.session.get(url, headers=self.get_headers(), timeout=timeout, verify=False)
            if response.status_code == 200:
                return BeautifulSoup(response.content, 'html.parser')
            return None
        except Exception:
            return None
    
    def chercher_page_bulletins(self, base_url: str) -> List[str]:
        """Trouve les pages de bulletins sur le site"""
        urls_bulletins = []
        
        # Tester les patterns courants
        for pattern in BULLETIN_PATTERNS:
            url = urljoin(base_url, pattern)
            soup = self.fetch_page(url)
            if soup:
                urls_bulletins.append(url)
        
        # Chercher sur la page d'accueil
        soup = self.fetch_page(base_url)
        if soup:
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').lower()
                text = link.get_text().lower()
                
                # Mots-clés bulletins
                if any(mot in href or mot in text for mot in ['bulletin', 'magazine', 'journal', 'publication', 'lettre']):
                    full_url = urljoin(base_url, link['href'])
                    if full_url not in urls_bulletins:
                        urls_bulletins.append(full_url)
        
        return urls_bulletins[:5]  # Limiter à 5 URLs max
    
    def chercher_bulletins_2026(self, url_bulletins: str, commune: str) -> List[str]:
        """Trouve les liens vers bulletins 2026"""
        bulletins_2026 = []
        soup = self.fetch_page(url_bulletins)
        
        if not soup:
            return []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text()
            
            # Chercher 2026 dans le lien ou le texte
            if '2026' in href or '2026' in text:
                full_url = urljoin(url_bulletins, href)
                if full_url not in bulletins_2026:
                    bulletins_2026.append(full_url)
        
        # Si pas de 2026, prendre les plus récents
        if not bulletins_2026:
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').lower()
                text = link.get_text().lower()
                if 'bulletin' in href or 'bulletin' in text or '.pdf' in href:
                    full_url = urljoin(url_bulletins, link['href'])
                    bulletins_2026.append(full_url)
                    if len(bulletins_2026) >= 3:
                        break
        
        return bulletins_2026[:5]
    
    def analyser_contenu(self, url: str, commune: str, dept: str) -> Optional[ProjetChaufferie]:
        """Analyse le contenu d'une page pour détecter projets chaufferie"""
        soup = self.fetch_page(url)
        if not soup:
            return None
        
        # Extraire tout le texte
        texte = soup.get_text(separator=' ', strip=True).lower()
        
        # Chercher mots-clés chaufferie
        mots_trouves = []
        for mot in MOTS_CLES_CHAUFFERIE:
            if mot.lower() in texte:
                mots_trouves.append(mot)
        
        # Si pas de mots-clés chaufferie, pas intéressant
        if not mots_trouves:
            return None
        
        # Chercher mots-clés contexte
        contexte_trouves = []
        for mot in MOTS_CLES_CONTEXTE:
            if mot.lower() in texte:
                contexte_trouves.append(mot)
        
        # Extraire un extrait pertinent
        extrait = self.extraire_passage_pertinent(texte, mots_trouves)
        
        # Estimer la phase du projet
        phase = self.estimer_phase(texte, contexte_trouves)
        
        # Chercher contact mairie
        contact = self.extraire_contact(soup)
        
        return ProjetChaufferie(
            commune=commune,
            departement=dept,
            source_type='bulletin' if 'bulletin' in url.lower() else 'page_municipale',
            date_publication=datetime.now().strftime('%Y-%m-%d'),
            titre=soup.title.string if soup.title else 'Sans titre',
            extrait=extrait[:500],
            mots_cles_trouves=mots_trouves + contexte_trouves,
            phase_estimee=phase,
            url_source=url,
            contact_mairie=contact
        )
    
    def extraire_passage_pertinent(self, texte: str, mots_cles: List[str]) -> str:
        """Extrait le passage contenant les mots-clés"""
        for mot in mots_cles:
            pos = texte.find(mot.lower())
            if pos != -1:
                debut = max(0, pos - 200)
                fin = min(len(texte), pos + 300)
                return texte[debut:fin].strip()
        return texte[:500]
    
    def estimer_phase(self, texte: str, contexte: List[str]) -> str:
        """Estime la phase du projet"""
        if any(mot in texte for mot in ['en cours', 'travaux', 'chantier', 'réalisation']):
            return 'en_cours'
        elif any(mot in texte for mot in ['appel d\'offre', 'consultation', 'marché']):
            return 'consultation'
        elif any(mot in texte for mot in ['étude', 'diagnostic', 'audit']):
            return 'etude'
        elif any(mot in texte for mot in ['projet', 'réflexion', 'envisag', 'programm']):
            return 'reflexion'
        return 'reflexion'
    
    def extraire_contact(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrait les contacts de la page"""
        contacts = []
        
        # Emails
        for match in re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', soup.get_text()):
            if match not in contacts:
                contacts.append(match)
        
        # Téléphones
        for match in re.findall(r'(?:0[1-9][\s\.\-]?(?:[0-9]{2}[\s\.\-]?){4})', soup.get_text()):
            tel = re.sub(r'[\s\.\-]', '', match)
            if tel not in contacts:
                contacts.append(tel)
        
        return ', '.join(contacts[:3]) if contacts else None
    
    def scanner_commune(self, commune_info: Dict):
        """Scanne une commune complète"""
        commune = commune_info['commune']
        dept = commune_info['dept']
        base_url = commune_info['url']
        
        print(f"  🔍 {commune} ({dept})")
        self.stats['communes_scannees'] += 1
        
        # Chercher pages bulletins
        urls_bulletins = self.chercher_page_bulletins(base_url)
        
        if urls_bulletins:
            print(f"    📰 {len(urls_bulletins)} pages bulletins trouvées")
            self.stats['bulletins_trouves'] += len(urls_bulletins)
            
            for url_bulletin in urls_bulletins:
                # Chercher bulletins 2026
                bulletins_2026 = self.chercher_bulletins_2026(url_bulletin, commune)
                
                for bulletin_url in bulletins_2026:
                    projet = self.analyser_contenu(bulletin_url, commune, dept)
                    if projet:
                        print(f"    🎯 PROJET DÉTECTÉ: {projet.mots_cles_trouves}")
                        self.projets_trouves.append(projet)
                        self.stats['projets_detectes'] += 1
                
                time.sleep(random.uniform(0.5, 1.5))
        else:
            # Analyser la page d'accueil directement
            projet = self.analyser_contenu(base_url, commune, dept)
            if projet:
                print(f"    🎯 PROJET DÉTECTÉ (accueil): {projet.mots_cles_trouves}")
                self.projets_trouves.append(projet)
                self.stats['projets_detectes'] += 1
        
        time.sleep(random.uniform(1, 2))
    
    def run(self):
        """Lance le scan complet"""
        print("🚀 SCRAPER BULLETINS MUNICIPAUX 2026")
        print("🎯 Objectif: Trouver des projets chaufferie comme Nivigne et Suran")
        print(f"📊 {len(COMMUNES_AURA)} communes AURA à scanner")
        print("=" * 60)
        
        for commune_info in COMMUNES_AURA:
            try:
                self.scanner_commune(commune_info)
            except Exception as e:
                print(f"    💥 Erreur: {str(e)[:50]}")
                self.stats['erreurs'] += 1
        
        self.generer_rapport()
    
    def generer_rapport(self):
        """Génère le rapport final"""
        print("\n" + "=" * 60)
        print("📊 RAPPORT FINAL")
        print("=" * 60)
        
        print(f"\n📈 STATISTIQUES:")
        print(f"  • Communes scannées: {self.stats['communes_scannees']}")
        print(f"  • Pages bulletins trouvées: {self.stats['bulletins_trouves']}")
        print(f"  • Projets détectés: {self.stats['projets_detectes']}")
        print(f"  • Erreurs: {self.stats['erreurs']}")
        
        if self.projets_trouves:
            print(f"\n🎯 PROJETS CHAUFFERIE DÉTECTÉS ({len(self.projets_trouves)}):")
            print("-" * 40)
            
            for i, projet in enumerate(self.projets_trouves, 1):
                print(f"\n{i}. 📍 {projet.commune} ({projet.departement})")
                print(f"   📄 Source: {projet.source_type}")
                print(f"   🎯 Phase: {projet.phase_estimee}")
                print(f"   🔑 Mots-clés: {', '.join(projet.mots_cles_trouves[:5])}")
                print(f"   📝 Extrait: {projet.extrait[:150]}...")
                if projet.contact_mairie:
                    print(f"   📞 Contact: {projet.contact_mairie}")
                print(f"   🔗 URL: {projet.url_source}")
            
            # Sauvegarder JSON
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f'projets_chaufferie_2026_{timestamp}.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump([asdict(p) for p in self.projets_trouves], f, ensure_ascii=False, indent=2)
            print(f"\n💾 Sauvegardé: {filename}")
        else:
            print("\n⚠️ Aucun projet détecté")
            print("💡 Recommandations:")
            print("  1. Élargir les mots-clés")
            print("  2. Ajouter plus de communes rurales")
            print("  3. Scanner les PDFs de bulletins")

# Désactiver les warnings SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

if __name__ == "__main__":
    scraper = ScraperBulletins2026()
    scraper.run()
