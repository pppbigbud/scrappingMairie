#!/usr/bin/env python3
"""
Test rapide API data.gouv.fr - Chaufferies Biomasse
Version simplifiée sans Playwright pour test immédiat
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
    departement: str
    source: str
    date: str
    titre: str
    description: str
    mots_cles: List[str]
    url_source: str
    confiance: str

# Mots-clés détection
MOTS_CLES_PRIORITAIRES = [
    'chaufferie', 'biomasse', 'chaudière bois', 'bois énergie', 'réseau chaleur',
    'chaufferie collective', 'chaudière biomasse', 'chaleur renouvelable'
]

MOTS_CLES_SECONDAIRES = [
    'chauffage collectif', 'granulés', 'plaquettes', 'modernisation chauffage',
    'remplacement chaudière', 'énergie renouvelable', 'transition énergétique'
]

class TestDataGouv:
    """Test simple de l'API data.gouv.fr"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ScraperTest/1.0)',
            'Accept': 'application/json'
        })

    def analyser_texte(self, texte: str) -> tuple[List[str], str]:
        """Analyse le texte pour détecter mots-clés"""
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
            
        return list(set(mots_trouves)), confiance  # Dédoublonnage

    def test_api_datasets(self) -> List[Opportunite]:
        """Test API datasets avec mots-clés chaufferie"""
        print("🔍 Test API data.gouv.fr - Recherche datasets...")
        
        opportunites = []
        
        # Plusieurs requêtes avec mots-clés différents
        requetes = [
            'chaufferie biomasse',
            'délibération chauffage bois',
            'conseil municipal énergie',
            'chaudière collective',
            'réseau chaleur'
        ]
        
        for requete in requetes:
            print(f"  🔎 Recherche: '{requete}'")
            
            url = "https://www.data.gouv.fr/api/1/datasets/"
            params = {
                'q': requete,
                'page_size': 20,
                'sort': '-created_at'
            }
            
            try:
                response = self.session.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    datasets = data.get('data', [])
                    print(f"    ✅ {len(datasets)} datasets trouvés")
                    
                    for dataset in datasets:
                        title = dataset.get('title', '')
                        description = dataset.get('description', '')
                        
                        # Analyser pertinence
                        texte_complet = f"{title} {description}"
                        mots_cles, confiance = self.analyser_texte(texte_complet)
                        
                        if mots_cles:  # Si pertinent
                            opportunites.append(Opportunite(
                                commune=dataset.get('organization', {}).get('name', 'Inconnue')[:50],
                                departement='Multi',
                                source='data.gouv',
                                date=dataset.get('created_at', '')[:10],
                                titre=title[:100],
                                description=description[:300],
                                mots_cles=mots_cles,
                                url_source=f"https://www.data.gouv.fr/fr/datasets/{dataset.get('slug', '')}",
                                confiance=confiance
                            ))
                            print(f"      🎯 TROUVÉ: {title[:50]}... (confiance: {confiance})")
                        
                else:
                    print(f"    ❌ Erreur HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"    ⚠️ Erreur requête: {e}")
                
            time.sleep(1)  # Pause entre requêtes
            
        return opportunites

    def test_api_actes_collectivites(self) -> List[Opportunite]:
        """Test API spécifique aux actes des collectivités"""
        print("\n🏛️ Test API actes des collectivités...")
        
        opportunites = []
        
        # URL spécialisée pour actes administratifs
        url = "https://www.data.gouv.fr/api/1/organizations/etalab/datasets/"
        
        try:
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                datasets = data.get('data', [])
                print(f"  📋 {len(datasets)} datasets Etalab trouvés")
                
                # Filtrer sur actes/délibérations
                for dataset in datasets:
                    title = dataset.get('title', '').lower()
                    description = dataset.get('description', '').lower()
                    
                    if any(mot in f"{title} {description}" for mot in ['acte', 'délibération', 'conseil', 'municipal']):
                        print(f"    📄 Pertinent: {dataset.get('title', '')[:60]}...")
                        
                        mots_cles, confiance = self.analyser_texte(f"{title} {description}")
                        
                        if mots_cles:
                            opportunites.append(Opportunite(
                                commune='Multi-collectivités',
                                departement='National',
                                source='data.gouv_actes',
                                date=dataset.get('created_at', '')[:10],
                                titre=dataset.get('title', '')[:100],
                                description=dataset.get('description', '')[:300],
                                mots_cles=mots_cles,
                                url_source=f"https://www.data.gouv.fr/fr/datasets/{dataset.get('slug', '')}",
                                confiance=confiance
                            ))
                            
        except Exception as e:
            print(f"  ❌ Erreur API actes: {e}")
            
        return opportunites

    def generer_rapport(self, opportunites: List[Opportunite]) -> str:
        """Génère rapport de test"""
        
        if not opportunites:
            return "❌ AUCUNE OPPORTUNITÉ DÉTECTÉE"
            
        # Stats
        stats_confiance = {'forte': 0, 'moyenne': 0, 'faible': 0}
        for opp in opportunites:
            stats_confiance[opp.confiance] += 1
            
        rapport = []
        rapport.append("🎯 RAPPORT TEST DATA.GOUV.FR")
        rapport.append("=" * 50)
        rapport.append(f"📊 Total: {len(opportunites)} opportunités")
        rapport.append(f"📈 Confiance: Forte={stats_confiance['forte']}, Moyenne={stats_confiance['moyenne']}, Faible={stats_confiance['faible']}")
        rapport.append("")
        
        # Top opportunités
        rapport.append("🔥 TOP OPPORTUNITÉS")
        rapport.append("-" * 30)
        
        # Trier par confiance
        fortes = [o for o in opportunites if o.confiance == 'forte'][:5]
        moyennes = [o for o in opportunites if o.confiance == 'moyenne'][:5]
        
        if fortes:
            rapport.append("💪 CONFIANCE FORTE:")
            for i, opp in enumerate(fortes, 1):
                rapport.append(f"{i}. 📍 {opp.commune}")
                rapport.append(f"   📰 {opp.titre}")
                rapport.append(f"   🎯 {', '.join(opp.mots_cles)}")
                rapport.append(f"   🌐 {opp.url_source}")
                rapport.append("")
        
        if moyennes:
            rapport.append("⚡ CONFIANCE MOYENNE:")
            for i, opp in enumerate(moyennes, 1):
                rapport.append(f"{i}. {opp.commune} - {opp.titre[:50]}...")
                rapport.append(f"   🎯 {', '.join(opp.mots_cles)}")
                rapport.append("")
                
        return "\n".join(rapport)

def main():
    """Test principal"""
    print("🚀 DÉMARRAGE TEST DATA.GOUV.FR")
    print("=" * 50)
    
    tester = TestDataGouv()
    start_time = time.time()
    
    # Tests
    opportunites_datasets = tester.test_api_datasets()
    opportunites_actes = tester.test_api_actes_collectivites()
    
    # Compilation
    toutes_opportunites = opportunites_datasets + opportunites_actes
    
    # Rapport
    rapport = tester.generer_rapport(toutes_opportunites)
    
    print(f"\n⏱️ TEST TERMINÉ EN {time.time() - start_time:.1f}s")
    print("=" * 50)
    print(rapport)
    
    # Sauvegarde
    if toutes_opportunites:
        filename = f'test_data_gouv_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([asdict(opp) for opp in toutes_opportunites], f, ensure_ascii=False, indent=2)
        print(f"\n💾 Sauvegardé: {filename}")

if __name__ == "__main__":
    main()