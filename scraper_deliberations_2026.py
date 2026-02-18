#!/usr/bin/env python3
"""
SCRAPER DÉLIBÉRATIONS 2026 - PROJETS AVANT APPELS D'OFFRES
Objectif: Détecter les projets chaufferie en phase de réflexion municipale
AVANT publication BOAMP (6-12 mois d'avance)
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Optional
import time
import random
from urllib.parse import urljoin, urlparse

@dataclass
class ProjetEnAmont:
    commune: str
    departement: str
    date_deliberation: str
    type_document: str  # 'deliberation', 'bulletin', 'actualite', 'pv_conseil'
    titre: str
    description: str
    mots_cles_detectes: List[str]
    phase_projet: str  # 'reflexion', 'etude', 'programmation', 'consultation'
    url_source: str
    confiance: str
    budget_mentionne: Optional[str] = None
    calendrier_mentionne: Optional[str] = None

# MOTS-CLÉS PHASE AMONT (avant appels d'offres)
MOTS_CLES_PHASE_AMONT = [
    # Études et réflexions
    'étude de faisabilité', 'étude préalable', 'étude énergétique',
    'diagnostic énergétique', 'audit énergétique', 'schéma directeur',
    
    # Programmation
    'programmation énergétique', 'planification énergétique',
    'stratégie énergétique', 'plan climat', 'transition énergétique',
    
    # Délibérations préparatoires
    'réflexion chaufferie', 'projet chaufferie', 'modernisation chauffage',
    'remplacement chaudière', 'nouveau système chauffage',
    
    # Budgets et subventions
    'demande subvention', 'financement énergie', 'budget chauffage',
    'crédit énergie', 'aide ADEME', 'fonds transition'
]

# MOTS-CLÉS TECHNIQUES CHAUFFERIE
MOTS_CLES_TECHNIQUES = [
    'chaufferie', 'biomasse', 'chaudière bois', 'bois énergie',
    'réseau chaleur', 'chauffage collectif', 'granulés',
    'plaquettes forestières', 'géothermie', 'pompe à chaleur'
]

# INDICATEURS TEMPORELS 2026
INDICATEURS_2026 = [
    'janvier 2026', 'février 2026', '2026', 'cette année',
    'prochainement', 'à venir', 'en projet', 'en réflexion'
]

# COMMUNES AUVERGNE-RHÔNE-ALPES PRIORITAIRES
COMMUNES_CIBLES_2026 = [
    # Puy-de-Dôme (63) - Focus sur moyennes communes (budgets suffisants)
    {'commune': 'Clermont-Ferrand', 'dept': '63', 'url': 'https://www.clermontferrand.fr', 'pop': 147284},
    {'commune': 'Riom', 'dept': '63', 'url': 'https://www.ville-riom.fr', 'pop': 18682},
    {'commune': 'Issoire', 'dept': '63', 'url': 'https://www.issoire.fr', 'pop': 13806},
    {'commune': 'Thiers', 'dept': '63', 'url': 'https://www.ville-thiers.fr', 'pop': 11634},
    {'commune': 'Cournon-d\'Auvergne', 'dept': '63', 'url': 'https://www.cournon-auvergne.fr', 'pop': 19627},
    
    # Allier (03)
    {'commune': 'Vichy', 'dept': '03', 'url': 'https://www.ville-vichy.fr', 'pop': 25789},
    {'commune': 'Montluçon', 'dept': '03', 'url': 'https://www.montlucon.fr', 'pop': 37570},
    {'commune': 'Moulins', 'dept': '03', 'url': 'https://www.moulins.fr', 'pop': 19960},
    
    # Cantal (15)
    {'commune': 'Aurillac', 'dept': '15', 'url': 'https://www.aurillac.fr', 'pop': 25411},
    {'commune': 'Saint-Flour', 'dept': '15', 'url': 'https://www.saint-flour.fr', 'pop': 6643},
    
    # Haute-Loire (43)  
    {'commune': 'Le Puy-en-Velay', 'dept': '43', 'url': 'https://www.lepuyenvelay.fr', 'pop': 18618},
    {'commune': 'Yssingeaux', 'dept': '43', 'url': 'https://www.yssingeaux.fr', 'pop': 7206},
    
    # Rhône (69) - Banlieues Lyon (budgets municipaux conséquents)
    {'commune': 'Villeurbanne', 'dept': '69', 'url': 'https://www.villeurbanne.fr', 'pop': 148543},
    {'commune': 'Vénissieux', 'dept': '69', 'url': 'https://www.venissieux.fr', 'pop': 64506},
    {'commune': 'Caluire-et-Cuire', 'dept': '69', 'url': 'https://www.caluire-et-cuire.fr', 'pop': 42729},
    
    # Isère (38)
    {'commune': 'Grenoble', 'dept': '38', 'url': 'https://www.grenoble.fr', 'pop': 158552},
    {'commune': 'Saint-Martin-d\'Hères', 'dept': '38', 'url': 'https://www.saintmartindheres.fr', 'pop': 37307},
    {'commune': 'Échirolles', 'dept': '38', 'url': 'https://www.echirolles.fr', 'pop': 35770},
]

class ScraperDeliberations2026:
    """Scraper spécialisé délibérations municipales 2026"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'DNT': '1',
            'Connection': 'keep-alive'
        })
        
        self.projets_detectes = []
        self.sites_testes = 0
        self.sites_accessibles = 0

    def analyser_contenu_amont(self, texte: str, titre: str = '') -> tuple[List[str], str, str]:
        """Analyse spécialisée pour détecter projets phase amont"""
        if not texte:
            return [], 'aucune', 'faible'
            
        texte_complet = f"{titre} {texte}".lower()
        
        # Détection mots-clés phase amont
        mots_amont = []
        for mot in MOTS_CLES_PHASE_AMONT:
            if mot.lower() in texte_complet:
                mots_amont.append(mot)
        
        # Détection mots-clés techniques
        mots_tech = []
        for mot in MOTS_CLES_TECHNIQUES:
            if mot.lower() in texte_complet:
                mots_tech.append(mot)
        
        # Tous les mots détectés
        tous_mots = list(set(mots_amont + mots_tech))
        
        # Détermination phase projet
        phase = 'aucune'
        if any(mot in texte_complet for mot in ['étude de faisabilité', 'étude préalable', 'diagnostic']):
            phase = 'etude'
        elif any(mot in texte_complet for mot in ['programmation', 'planification', 'stratégie']):
            phase = 'programmation'  
        elif any(mot in texte_complet for mot in ['réflexion', 'projet', 'envisage']):
            phase = 'reflexion'
        elif any(mot in texte_complet for mot in ['consultation', 'appel', 'marché']):
            phase = 'consultation'
        
        # Calcul confiance
        score_amont = len(mots_amont)
        score_tech = len(mots_tech)
        
        if score_amont >= 2 and score_tech >= 1:
            confiance = 'forte'  # Phase amont + technique = parfait
        elif score_amont >= 1 and score_tech >= 1:
            confiance = 'moyenne'
        elif tous_mots:
            confiance = 'faible'
        else:
            confiance = 'nulle'
            
        return tous_mots, phase, confiance

    def extraire_budget_calendrier(self, texte: str) -> tuple[Optional[str], Optional[str]]:
        """Extraction budget et calendrier des délibérations"""
        
        budget = None
        calendrier = None
        
        # Patterns budget
        patterns_budget = [
            r'budget[^\d]*(\d{1,3}(?:[\s\.,]\d{3})*)\s*(?:€|euros?)',
            r'crédit[^\d]*(\d{1,3}(?:[\s\.,]\d{3})*)\s*(?:€|euros?)',
            r'financement[^\d]*(\d{1,3}(?:[\s\.,]\d{3})*)\s*(?:€|euros?)',
            r'(\d{1,3}(?:[\s\.,]\d{3})*)\s*(?:€|euros?)'
        ]
        
        for pattern in patterns_budget:
            match = re.search(pattern, texte, re.IGNORECASE)
            if match:
                budget = match.group(1)
                break
        
        # Patterns calendrier
        patterns_calendrier = [
            r'(2026|2027|2028)',
            r'(premier semestre|deuxième semestre)',
            r'(printemps|été|automne|hiver)\s*202[6-8]',
            r'(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*202[6-8]'
        ]
        
        for pattern in patterns_calendrier:
            match = re.search(pattern, texte, re.IGNORECASE)
            if match:
                calendrier = match.group(1)
                break
        
        return budget, calendrier

    def chercher_deliberations_recentes(self, commune_info: dict) -> List[ProjetEnAmont]:
        """Recherche délibérations récentes d'une commune"""
        
        commune = commune_info['commune']
        url_base = commune_info['url']
        dept = commune_info['dept']
        
        print(f"  🔍 {commune}")
        
        self.sites_testes += 1
        projets_commune = []
        
        try:
            # Accès site principal
            response = self.session.get(url_base, timeout=15)
            print(f"    📊 Status: {response.status_code}")
            
            if response.status_code != 200:
                return []
            
            self.sites_accessibles += 1
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. RECHERCHE LIENS DÉLIBÉRATIONS/CONSEILS
            patterns_liens = [
                'a[href*="deliberation"]', 'a[href*="conseil"]', 
                'a[href*="municipal"]', 'a[href*="seance"]',
                'a[href*="pv"]', 'a[href*="proces"]', 'a[href*="verbaux"]',
                'a[href*="actualit"]', 'a[href*="info"]', 'a[href*="bulletin"]'
            ]
            
            liens_interessants = []
            for pattern in patterns_liens:
                for lien in soup.select(pattern):
                    href = lien.get('href', '')
                    text = lien.get_text(strip=True)
                    
                    # Filtrer sur 2026 ou mots récents
                    if any(mot in text.lower() for mot in ['2026', 'janvier', 'février', 'récent', 'dernier']):
                        if href.startswith('/'):
                            href = urljoin(url_base, href)
                        elif href.startswith('http'):
                            pass
                        else:
                            continue
                            
                        liens_interessants.append({
                            'text': text,
                            'url': href,
                            'type': self._determiner_type_document(text)
                        })
            
            print(f"    📋 {len(liens_interessants)} liens 2026 trouvés")
            
            # 2. EXPLORATION DES LIENS (max 8 par commune)
            for lien in liens_interessants[:8]:
                try:
                    time.sleep(random.uniform(1, 2))  # Pause respectueuse
                    
                    doc_response = self.session.get(lien['url'], timeout=12)
                    
                    if doc_response.status_code == 200:
                        # Parse document
                        if lien['url'].endswith('.pdf'):
                            # PDF → analyse titre uniquement (pas de parsing PDF)
                            texte_doc = lien['text']
                            titre_doc = lien['text']
                        else:
                            # HTML → analyse complète
                            doc_soup = BeautifulSoup(doc_response.content, 'html.parser')
                            texte_doc = doc_soup.get_text()
                            titre_doc = doc_soup.find('title').get_text() if doc_soup.find('title') else lien['text']
                        
                        # Analyse contenu
                        mots_cles, phase, confiance = self.analyser_contenu_amont(texte_doc, titre_doc)
                        
                        if mots_cles and confiance != 'nulle':
                            budget, calendrier = self.extraire_budget_calendrier(texte_doc)
                            
                            projets_commune.append(ProjetEnAmont(
                                commune=commune,
                                departement=dept,
                                date_deliberation='2026-01/02',  # Estimation
                                type_document=lien['type'],
                                titre=titre_doc[:150],
                                description=texte_doc[:500],
                                mots_cles_detectes=mots_cles,
                                phase_projet=phase,
                                url_source=lien['url'],
                                confiance=confiance,
                                budget_mentionne=budget,
                                calendrier_mentionne=calendrier
                            ))
                            
                            print(f"    ✅ Projet détecté: {phase} - {', '.join(mots_cles[:3])} ({confiance})")
                
                except Exception as e:
                    print(f"    ⚠️ Erreur lien {lien['url']}: {e}")
        
        except Exception as e:
            print(f"    💥 Erreur commune: {e}")
        
        return projets_commune

    def _determiner_type_document(self, text: str) -> str:
        """Détermine le type de document depuis le texte du lien"""
        text_lower = text.lower()
        
        if any(mot in text_lower for mot in ['délibération', 'deliberation']):
            return 'deliberation'
        elif any(mot in text_lower for mot in ['conseil', 'séance', 'pv', 'procès']):
            return 'pv_conseil'
        elif any(mot in text_lower for mot in ['bulletin', 'magazine', 'journal']):
            return 'bulletin'
        elif any(mot in text_lower for mot in ['actualité', 'info', 'news']):
            return 'actualite'
        else:
            return 'autre'

    def executer_veille_2026(self) -> List[ProjetEnAmont]:
        """Exécution de la veille délibérations 2026"""
        
        print("🚀 VEILLE DÉLIBÉRATIONS 2026 - PROJETS AVANT APPELS D'OFFRES")
        print("🎯 Cible: Projets chaufferie phase amont (6-12 mois avant BOAMP)")
        print("📅 Focus: Délibérations janvier-février 2026")
        print("=" * 70)
        
        start_time = time.time()
        
        for commune_info in COMMUNES_CIBLES_2026[:10]:  # Test sur 10 communes d'abord
            projets = self.chercher_deliberations_recentes(commune_info)
            self.projets_detectes.extend(projets)
            
            # Pause entre communes
            time.sleep(random.uniform(3, 5))
        
        duree = time.time() - start_time
        print(f"\n⏱️ Veille terminée en {duree/60:.1f} minutes")
        print(f"📊 Sites testés: {self.sites_testes}")
        print(f"✅ Sites accessibles: {self.sites_accessibles}")
        print(f"🎯 Projets phase amont détectés: {len(self.projets_detectes)}")
        
        return self.projets_detectes

    def generer_rapport_amont(self, projets: List[ProjetEnAmont]) -> str:
        """Rapport spécialisé projets phase amont"""
        
        if not projets:
            return """❌ AUCUN PROJET PHASE AMONT DÉTECTÉ
            
🔍 RAISONS POSSIBLES:
- Délibérations 2026 pas encore publiées en ligne
- Terminologie différente des mots-clés recherchés  
- Projets encore en phase très amont (non documentée)
- Sites municipaux avec délais de publication

🚀 RECOMMANDATIONS:
1. Élargir mots-clés: "rénovation", "efficacité énergétique"
2. Surveiller bulletins municipaux (février-mars 2026)  
3. Contacter directement services techniques
4. Automatiser veille quotidienne Mars-Avril 2026"""
        
        # Statistiques
        stats_phase = {}
        stats_confiance = {'forte': 0, 'moyenne': 0, 'faible': 0}
        stats_dept = {}
        
        for projet in projets:
            stats_phase[projet.phase_projet] = stats_phase.get(projet.phase_projet, 0) + 1
            stats_confiance[projet.confiance] += 1
            stats_dept[projet.departement] = stats_dept.get(projet.departement, 0) + 1
        
        rapport = []
        rapport.append("🎯 VEILLE PROJETS AVANT APPELS D'OFFRES 2026")
        rapport.append("=" * 60)
        rapport.append(f"🏆 MISSION FRANK: Détection projets phase amont")
        rapport.append(f"  • 🎯 Projets détectés: {len(projets)}")
        rapport.append(f"  • 📊 Phases: {dict(stats_phase)}")
        rapport.append(f"  • 🎖️ Confiance: Forte={stats_confiance['forte']}, Moyenne={stats_confiance['moyenne']}")
        rapport.append(f"  • 🗺️ Départements: {dict(stats_dept)}")
        rapport.append("")
        
        # Projets par phase (priorité aux plus avancés)
        phases_ordre = ['consultation', 'etude', 'programmation', 'reflexion']
        
        for phase in phases_ordre:
            projets_phase = [p for p in projets if p.phase_projet == phase]
            if projets_phase:
                titre_phase = {
                    'consultation': '🔴 CONSULTATION (Urgent - Proche appel offre)',
                    'etude': '🟠 ÉTUDE (Très intéressant - 6 mois avance)',
                    'programmation': '🟡 PROGRAMMATION (Bon timing - 9 mois)',
                    'reflexion': '🟢 RÉFLEXION (À surveiller - 12+ mois)'
                }[phase]
                
                rapport.append(titre_phase)
                rapport.append("=" * len(titre_phase))
                
                for i, projet in enumerate(projets_phase, 1):
                    rapport.append(f"{i}. 📍 {projet.commune} ({projet.departement})")
                    rapport.append(f"   📅 {projet.date_deliberation} | 📄 {projet.type_document}")
                    rapport.append(f"   📰 {projet.titre}")
                    rapport.append(f"   🎯 Mots-clés: {', '.join(projet.mots_cles_detectes)}")
                    if projet.budget_mentionne:
                        rapport.append(f"   💰 Budget: {projet.budget_mentionne}€")
                    if projet.calendrier_mentionne:
                        rapport.append(f"   📅 Calendrier: {projet.calendrier_mentionne}")
                    rapport.append(f"   🌐 {projet.url_source}")
                    rapport.append("")
        
        # Conclusion pour entretien
        rapport.append("💼 VALEUR POUR TON ENTRETIEN")
        rapport.append("=" * 35)
        
        if len(projets) >= 3:
            rapport.append("🏆 EXCELLENT - Tu as l'avance stratégique!")
            rapport.append("💰 Projets détectés 6-12 mois avant concurrence")
            rapport.append("📈 Avantage concurrentiel démontré")
        elif len(projets) >= 1:
            rapport.append("✅ BON DÉBUT - Concept validé")
            rapport.append("🔧 Système fonctionnel, à affiner")
        else:
            rapport.append("⚠️ RÉSULTATS À DÉVELOPPER")
            rapport.append("💡 Montrer le potentiel technique")
        
        return "\n".join(rapport)

def main():
    """Fonction principale - Veille 2026"""
    
    scraper = ScraperDeliberations2026()
    
    # Exécution veille
    projets = scraper.executer_veille_2026()
    
    # Rapport
    rapport = scraper.generer_rapport_amont(projets)
    
    print("\n" + "=" * 80)
    print("📋 RAPPORT VEILLE 2026 POUR FRANK")
    print("=" * 80)
    print(rapport)
    
    # Sauvegarde
    if projets:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f'projets_amont_2026_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([asdict(p) for p in projets], f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Projets sauvegardés: {filename}")
    
    print(f"\n🎯 MESSAGE FRANK:")
    if len(projets) >= 2:
        print("✅ BINGO! Tu as des projets en avance sur la concurrence!")
    else:
        print("🔄 On continue - Mars 2026 sera plus riche en délibérations!")

if __name__ == "__main__":
    main()