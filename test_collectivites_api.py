#!/usr/bin/env python3
"""
Test API officielle des collectivités territoriales
Focus sur les actes administratifs et délibérations
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

# Mots-clés optimisés
MOTS_CLES = [
    'chaufferie', 'biomasse', 'chaudière bois', 'bois énergie', 'réseau chaleur',
    'chauffage collectif', 'granulés', 'plaquettes', 'énergie renouvelable'
]

class TestCollectivitesAPI:
    """Test des APIs spécialisées collectivités"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; VeilleEnergie/1.0)',
            'Accept': 'application/json, text/html'
        })

    def analyser_texte(self, texte: str) -> tuple[List[str], str]:
        """Détecte mots-clés et évalue confiance"""
        if not texte:
            return [], 'faible'
            
        texte_lower = texte.lower()
        mots_trouves = []
        
        for mot in MOTS_CLES:
            if mot.lower() in texte_lower:
                mots_trouves.append(mot)
        
        confiance = 'forte' if len(mots_trouves) >= 2 else ('moyenne' if mots_trouves else 'faible')
        return list(set(mots_trouves)), confiance

    def test_api_sirene(self) -> List[Opportunite]:
        """Test API Sirene pour identifier collectivités"""
        print("🏢 Test API Sirene - Collectivités Auvergne")
        
        opportunites = []
        
        # API Sirene - recherche établissements publics Auvergne
        url = "https://api.insee.fr/entreprises/sirene/v3/siret"
        
        # Codes NAF administration publique
        codes_naf = ['8411Z', '8412Z']  # Admin publique générale/locale
        
        for code in codes_naf:
            params = {
                'q': f'activitePrincipaleEtablissement:{code} AND (denominationUniteLegale:*mairie* OR denominationUniteLegale:*commune*)',
                'nombre': 20
            }
            
            try:
                response = self.session.get(url, params=params, timeout=10)
                print(f"  📋 Code {code}: Status {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    etablissements = data.get('etablissements', [])
                    print(f"    ✅ {len(etablissements)} établissements trouvés")
                    
            except Exception as e:
                print(f"    ❌ Erreur: {e}")
                
        return opportunites

    def test_api_marchespublics(self) -> List[Opportunite]:
        """Test API marchés publics pour chaufferies"""
        print("\n💰 Test API marchés publics BOAMP")
        
        opportunites = []
        
        # Différentes URLs à tester
        urls_test = [
            "https://www.boamp.fr/api/v2/search",  # API BOAMP v2
            "https://data.gouv.fr/api/1/datasets/?q=marchés",  # Datasets marchés
            "https://api.demarches-simplifiees.fr/graphql"  # Démarches simplifiées
        ]
        
        for url in urls_test:
            print(f"  🔗 Test: {url}")
            try:
                if 'graphql' in url:
                    # Query GraphQL pour démarches simplifiées
                    query = {
                        'query': '''
                        query {
                          demarchesPubliques(first: 10) {
                            edges {
                              node {
                                title
                                description
                              }
                            }
                          }
                        }
                        '''
                    }
                    response = self.session.post(url, json=query, timeout=10)
                else:
                    # Requête GET classique
                    params = {'q': 'chaufferie biomasse', 'size': 10}
                    response = self.session.get(url, params=params, timeout=10)
                
                print(f"    📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"    ✅ JSON valide: {len(str(data))} caractères")
                    except:
                        print(f"    📝 HTML/Text: {len(response.text)} caractères")
                        
            except Exception as e:
                print(f"    ❌ Erreur: {e}")
                
        return opportunites

    def test_web_scraping_simple(self) -> List[Opportunite]:
        """Test scraping simple sites officiels"""
        print("\n🌐 Test scraping sites officiels")
        
        opportunites = []
        
        # Sites officiels à tester
        sites_test = [
            {'url': 'https://www.clermontferrand.fr', 'commune': 'Clermont-Ferrand'},
            {'url': 'https://www.aurillac.fr', 'commune': 'Aurillac'},
            {'url': 'https://www.vichy.fr', 'commune': 'Vichy'}
        ]
        
        for site in sites_test:
            print(f"  🌍 Test: {site['commune']} ({site['url']})")
            
            try:
                response = self.session.get(site['url'], timeout=10)
                print(f"    📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    contenu = response.text.lower()
                    mots_cles, confiance = self.analyser_texte(contenu)
                    
                    if mots_cles:
                        opportunites.append(Opportunite(
                            commune=site['commune'],
                            departement='Test',
                            source='web_scraping',
                            date=datetime.now().strftime('%Y-%m-%d'),
                            titre=f"Site web {site['commune']}",
                            description=f"Contenu détecté sur le site officiel",
                            mots_cles=mots_cles,
                            url_source=site['url'],
                            confiance=confiance
                        ))
                        print(f"    🎯 TROUVÉ: {', '.join(mots_cles)} (confiance: {confiance})")
                    else:
                        print(f"    ⚪ Pas de mots-clés pertinents")
                        
            except Exception as e:
                print(f"    ❌ Erreur: {e}")
                
            time.sleep(2)  # Pause respectueuse
            
        return opportunites

    def test_rss_feeds(self) -> List[Opportunite]:
        """Test flux RSS des collectivités"""
        print("\n📡 Test flux RSS collectivités")
        
        opportunites = []
        
        # URLs RSS à tester
        rss_urls = [
            {'url': 'https://www.clermontferrand.fr/rss.xml', 'commune': 'Clermont-Ferrand'},
            {'url': 'https://www.aurillac.fr/rss', 'commune': 'Aurillac'},
            {'url': 'https://www.lepuyenvelay.fr/feed/', 'commune': 'Le Puy-en-Velay'}
        ]
        
        for rss in rss_urls:
            print(f"  📡 Test RSS: {rss['commune']}")
            
            try:
                response = self.session.get(rss['url'], timeout=10)
                print(f"    📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    contenu = response.text
                    mots_cles, confiance = self.analyser_texte(contenu)
                    
                    if mots_cles:
                        opportunites.append(Opportunite(
                            commune=rss['commune'],
                            departement='RSS',
                            source='rss_feed',
                            date=datetime.now().strftime('%Y-%m-%d'),
                            titre=f"Flux RSS {rss['commune']}",
                            description="Actualités détectées via RSS",
                            mots_cles=mots_cles,
                            url_source=rss['url'],
                            confiance=confiance
                        ))
                        print(f"    🎯 TROUVÉ: {', '.join(mots_cles)}")
                        
            except Exception as e:
                print(f"    ❌ Erreur: {e}")
                
        return opportunites

    def generer_rapport(self, opportunites: List[Opportunite]) -> str:
        """Rapport final"""
        
        if not opportunites:
            return "❌ AUCUNE OPPORTUNITÉ DÉTECTÉE DANS LES TESTS"
            
        # Stats par source
        stats_source = {}
        stats_confiance = {'forte': 0, 'moyenne': 0, 'faible': 0}
        
        for opp in opportunites:
            stats_source[opp.source] = stats_source.get(opp.source, 0) + 1
            stats_confiance[opp.confiance] += 1
            
        rapport = []
        rapport.append("🎯 RAPPORT FINAL - TESTS API COLLECTIVITÉS")
        rapport.append("=" * 60)
        rapport.append(f"📊 Total opportunités: {len(opportunites)}")
        rapport.append(f"📈 Sources: {stats_source}")
        rapport.append(f"🎯 Confiance: {stats_confiance}")
        rapport.append("")
        
        # Détail des opportunités
        rapport.append("🔥 OPPORTUNITÉS DÉTECTÉES")
        rapport.append("-" * 40)
        
        for i, opp in enumerate(opportunites, 1):
            rapport.append(f"{i}. 📍 {opp.commune} ({opp.source})")
            rapport.append(f"   📅 {opp.date} | 🎯 {opp.confiance}")
            rapport.append(f"   🔍 {', '.join(opp.mots_cles)}")
            rapport.append(f"   🌐 {opp.url_source}")
            rapport.append("")
            
        return "\n".join(rapport)

def main():
    """Test complet"""
    print("🚀 DÉMARRAGE TESTS API COLLECTIVITÉS")
    print("=" * 60)
    
    tester = TestCollectivitesAPI()
    start_time = time.time()
    
    # Tous les tests
    toutes_opportunites = []
    
    # Test 1: API Sirene
    toutes_opportunites.extend(tester.test_api_sirene())
    
    # Test 2: API marchés publics
    toutes_opportunites.extend(tester.test_api_marchespublics())
    
    # Test 3: Web scraping simple
    toutes_opportunites.extend(tester.test_web_scraping_simple())
    
    # Test 4: Flux RSS
    toutes_opportunites.extend(tester.test_rss_feeds())
    
    # Rapport final
    rapport = tester.generer_rapport(toutes_opportunites)
    
    print(f"\n⏱️ TOUS TESTS TERMINÉS EN {time.time() - start_time:.1f}s")
    print("=" * 60)
    print(rapport)
    
    # Sauvegarde si résultats
    if toutes_opportunites:
        filename = f'test_collectivites_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([asdict(opp) for opp in toutes_opportunites], f, ensure_ascii=False, indent=2)
        print(f"\n💾 Sauvegardé: {filename}")
    
    # Recommandations
    print("\n💡 RECOMMANDATIONS:")
    if toutes_opportunites:
        print("✅ Des sources fonctionnent ! On peut les développer")
        sources_ok = list(set(opp.source for opp in toutes_opportunites))
        print(f"📈 Sources prometteuses: {', '.join(sources_ok)}")
    else:
        print("⚠️ Aucune source ne fonctionne comme prévu")
        print("🔄 Il faut ajuster l'approche ou les APIs utilisées")

if __name__ == "__main__":
    main()