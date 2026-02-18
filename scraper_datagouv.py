#!/usr/bin/env python3
"""
Scraper de délibérations data.gouv.fr - Puy-de-Dôme
Recherche les projets chaufferie/biomasse dans les actes des communes
"""

import requests
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional
import time

@dataclass
class Opportunite:
    commune: str
    code_insee: str
    departement: str
    date_publication: str
    titre: str
    description: str
    mots_cles: List[str]
    url_source: str
    url_pdf: Optional[str] = None
    confiance: str = "moyenne"

# Mots-clés pour la détection
KEYWORDS_PRIORITAIRES = ['chaufferie', 'biomasse', 'chaudière bois', 'chaudière biomasse', 
                         'bois énergie', 'réseau chaleur', 'chaleur renouvelable']
KEYWORDS_SECONDAIRES = ['chauffage collectif', 'granulés', 'plaquettes', 'chaufferie collective',
                        'modernisation chauffage', 'remplacement chaudière']

class ScraperDataGouv:
    """Scraper pour data.gouv.fr / actes des collectivités"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.base_url = "https://www.data.gouv.fr/api/1"
        
    def rechercher_actes(self, query: str, departement: str = "63", 
                        taille_min: int = 1000, max_results: int = 50) -> List[Opportunite]:
        """
        Recherche les actes sur data.gouv.fr
        
        Args:
            query: terme de recherche (ex: "chaufferie")
            departement: numéro de département (63 pour Puy-de-Dôme)
            taille_min: population minimale des communes
            max_results: nombre max de résultats
        """
        opportunites = []
        
        # API data.gouv pour chercher les datasets
        search_url = f"{self.base_url}/datasets/"
        params = {
            'q': f"{query} délibération {departement}",
            'page_size': max_results
        }
        
        try:
            print(f"🔍 Recherche: '{query}' dans le {departement}...")
            resp = self.session.get(search_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            datasets = data.get('data', [])
            print(f"   📊 {len(datasets)} datasets trouvés")
            
            for dataset in datasets[:max_results]:
                opp = self._analyser_dataset(dataset, departement)
                if opp:
                    opportunites.append(opp)
                time.sleep(0.2)  # Respect API
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            
        return opportunites
    
    def _analyser_dataset(self, dataset: dict, departement: str) -> Optional[Opportunite]:
        """Analyse un dataset pour détecter un projet chaufferie"""
        titre = dataset.get('title', '').lower()
        description = dataset.get('description', '').lower() if dataset.get('description') else ''
        
        # Chercher les mots-clés
        mots_trouves = []
        for mot in KEYWORDS_PRIORITAIRES:
            if mot in titre or mot in description:
                mots_trouves.append(mot)
                
        for mot in KEYWORDS_SECONDAIRES:
            if mot in titre or mot in description:
                mots_trouves.append(mot)
        
        if not mots_trouves:
            return None
        
        # Déterminer confiance
        nb_prioritaires = sum(1 for m in mots_trouves if m in KEYWORDS_PRIORITAIRES)
        confiance = 'forte' if nb_prioritaires >= 2 else 'moyenne'
        
        # Extraire commune
        titre_orig = dataset.get('title', '')
        commune = self._extraire_commune(titre_orig)
        
        # Extraire date
        date_pub = dataset.get('created_at', dataset.get('last_update', 'Non daté'))
        if date_pub and 'T' in date_pub:
            date_pub = date_pub.split('T')[0]
        
        return Opportunite(
            commune=commune or "Non identifiée",
            code_insee="",
            departement=f"Puy-de-Dôme ({departement})",
            date_publication=date_pub,
            titre=dataset.get('title', 'Sans titre')[:100],
            description=dataset.get('description', 'Pas de description')[:200] + "..." if dataset.get('description') else "Pas de description",
            mots_cles=mots_trouves[:5],
            url_source=dataset.get('page', ''),
            confiance=confiance
        )
    
    def _extraire_commune(self, texte: str) -> Optional[str]:
        """Tente d'extraire le nom de la commune du titre"""
        # Patterns communs
        patterns = [
            r'([A-Za-z\-\s]+)\s*-\s*délibération',
            r'([A-Za-z\-\s]+)\s*\d{4}',
            r'commune\s+d[\'e]\s*([A-Za-z\-\s]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, texte, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
    
    def scraper_puy_de_dome(self, taille_commune: str = "moyenne") -> List[Opportunite]:
        """
        Lance le scraping complet sur le Puy-de-Dôme
        
        Args:
            taille_commune: "petite" (<2000), "moyenne" (2000-10000), "grande" (>10000)
        """
        print("=" * 70)
        print("🔥 SCRAPING DATA.GOUV.FR - PUy-DE-DÔME (63)")
        print("=" * 70)
        
        toutes_opps = []
        
        # Recherche avec différents termes
        termes_recherche = [
            'chaufferie biomasse',
            'chaudière bois',
            'réseau chaleur',
            'chauffage collectif',
            'énergie renouvelable chauffage'
        ]
        
        for terme in termes_recherche:
            opps = self.rechercher_actes(terme, departement="63")
            toutes_opps.extend(opps)
            time.sleep(0.5)
        
        # Dédupliquer par titre
        seen = set()
        uniques = []
        for opp in toutes_opps:
            if opp.titre not in seen:
                seen.add(opp.titre)
                uniques.append(opp)
        
        # Trier par date (plus récent en premier)
        uniques.sort(key=lambda x: x.date_publication, reverse=True)
        
        print("\n" + "=" * 70)
        print(f"📊 TOTAL: {len(uniques)} opportunités uniques détectées")
        print("=" * 70)
        
        return uniques
    
    def exporter_json(self, opportunites: List[Opportunite], filename: str = "resultats_scraping.json"):
        """Exporte les résultats en JSON"""
        data = [asdict(opp) for opp in opportunites]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Exporté dans {filename}")


def main():
    """Point d'entrée pour test CLI"""
    scraper = ScraperDataGouv()
    
    # Test sur Puy-de-Dôme
    resultats = scraper.scraper_puy_de_dome(taille_commune="moyenne")
    
    # Afficher les meilleures opportunités
    print("\n🎯 TOP OPPORTUNITÉS:")
    print("-" * 70)
    for i, opp in enumerate(resultats[:10], 1):
        emoji = "🔴" if opp.confiance == "forte" else "🟠"
        print(f"\n{i}. {emoji} {opp.commune}")
        print(f"   📅 {opp.date_publication}")
        print(f"   📝 {opp.titre[:60]}...")
        print(f"   🔑 {', '.join(opp.mots_cles[:3])}")
        print(f"   🔗 {opp.url_source[:50]}...")
    
    # Export
    if resultats:
        scraper.exporter_json(resultats)
    else:
        print("\n🤷 Aucune opportunité trouvée dans data.gouv.fr")
        print("💡 Essaie avec d'autres termes ou vérifie la connexion")


if __name__ == '__main__':
    main()