#!/usr/bin/env python3
"""
POC Veille Chaufferie Biomasse - Auvergne
Détecte les projets chaufferie dans les délibérations municipales
avant publication sur le BOAMP

Usage: python poc_veille_chaufferie.py
"""

import requests
import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
import json
import time

@dataclass
class Opportunite:
    """Représente une opportunité détectée"""
    commune: str
    departement: str
    date_delib: str
    titre: str
    mots_cles_trouves: List[str]
    url_source: str
    confiance: str  # 'forte', 'moyenne', 'faible'
    montant_estime: Optional[str] = None
    description: str = ""

# Liste des communes intéressantes (> 1000 habitants typiquement)
# Qui peuvent avoir des chaufferies collectives
COMMUNES_CIBLEES = {
    'Puy-de-Dôme': [
        'Clermont-Ferrand', 'Cournon', 'Riom', 'Chamalières', 'Issoire',
        'Thiers', 'Royat', 'Le Mont-Dore', 'La Bourboule', 'Ambert',
        'Ceyrat', 'Beaumont', 'Gerzat', 'Pérignat-lès-Sarliève',
        'Pont-du-Château', 'Aubière', 'Châteaugay', 'Billom',
        'Vic-le-Comte', 'Saint-Ours', 'Arlanc', 'Saint-Anthème'
    ],
    'Allier': [
        'Vichy', 'Montluçon', 'Moulins', 'Cusset', 'Yzeure',
        'Varennes-sur-Allier', 'Bellerive-sur-Allier', 'Saint-Pourçain',
        'Commentry', 'Gannat', 'Domérat', 'Saint-Yorre', 'Huriel'
    ],
    'Cantal': [
        'Aurillac', 'Saint-Flour', 'Mauriac', 'Murat', 'Vic-sur-Cère',
        'Arpajon-sur-Cère', 'Maurs', 'Pleaux', 'Chaudes-Aigues',
        'Riom-ès-Montagnes', 'Naucelles', 'Ydes'
    ],
    'Haute-Loire': [
        'Le Puy-en-Velay', 'Yssingeaux', 'Brioude', 'Monistrol-sur-Loire',
        'Polignac', 'Langeac', 'Saint-Paulien', 'Chadrac', 'Coubon',
        'Loudes', 'Saint-Didier-en-Velay', 'Cussac-sur-Loire'
    ]
}

# Mots-clés pour détecter les projets chaufferie biomasse
MOTS_CLES_PRIORITAIRES = [
    'chaufferie', 'biomasse', 'bois énergie', 'chaudière bois',
    'chaudière biomasse', 'poêle collectif', 'chauffage collectif',
    'énergie renouvelable', 'chaleur renouvelable', 'réseau chaleur'
]

MOTS_CLES_SECONDAIRES = [
    'chauffage bois', 'granulés', 'plaquettes', 'bûche',
    'chaufferie collective', 'chaudière collective', 'remplacement chaudière',
    'modernisation chauffage', 'chaufferie urbaine', 'chauffage municipal'
]

MOTS_CLES_BUDGET = [
    'budget', 'crédit', 'dépense', 'investissement', 'subvention',
    'fonds chaleur', 'ademe', 'denormandie', 'cee'
]

class VeilleChaufferie:
    """Moteur de veille pour les projets chaufferie biomasse"""
    
    def __init__(self):
        self.opportunites = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scraper_deliberations_mairie(self, commune: str, departement: str) -> List[dict]:
        """
        Simule le scraping des délibérations d'une mairie
        En production, utiliserai BeautifulSoup + Playwright pour le JS
        """
        # URLs typiques où trouver les délibérations
        urls_types = [
            f"https://www.{commune.lower().replace(' ', '-').replace("'", '')}.fr/deliberations",
            f"https://{commune.lower().replace(' ', '-').replace("'", '')}.fr/les-deliberations",
            f"https://www.mairie-{commune.lower().replace(' ', '-').replace("'", '')}.fr/documents",
        ]
        
        # Simuler des résultats pour le POC
        # En vrai: faire du vrai scraping avec gestion PDF/HTML
        return self._simuler_resultats(commune, departement)
    
    def _simuler_resultats(self, commune: str, departement: str) -> List[dict]:
        """Simule des délibérations pour le POC - à remplacer par vrai scraping"""
        resultats = []
        
        # Quelques exemples fictifs mais réalistes pour la démo
        exemples = [
            {
                'commune': 'Ambert',
                'titre': 'Délibération attribution marché chaufferie biomasse école primaire',
                'date': '2024-11-15',
                'contenu': 'Le conseil municipal autorise l\'attribution du marché de réhabilitation de la chaufferie bois de l\'école Jean Moulin pour un montant de 180 000€ HT',
                'confiance': 'forte'
            },
            {
                'commune': 'Thiers',
                'titre': 'Vote budget investissement 2025 - ligne chaufferie collective',
                'date': '2024-10-20',
                'contenu': 'Crédits ouverts pour études préalables chaufferie biomasse salle des fêtes. Montant estimé: 250 000€',
                'confiance': 'forte'
            },
            {
                'commune': 'Yzeure',
                'titre': 'Délibération subvention Fonds Chaleur - projet biomasse',
                'date': '2024-09-10',
                'contenu': 'Demande de subvention FD Chaleur pour installation chaudière bois plaquettes chauffage collectif immeuble seniors',
                'confiance': 'forte'
            },
            {
                'commune': 'Riom',
                'titre': 'Conseil municipal - étude de faisabilité énergétique',
                'date': '2024-08-05',
                'contenu': 'Engagement dépense pour étude préalable réseau chaleur quartier St Amable. Objectif: valoriser biomasse locale',
                'confiance': 'moyenne'
            }
        ]
        
        # Filtrer pour la commune demandée
        for ex in exemples:
            if ex['commune'].lower() == commune.lower():
                resultats.append(ex)
        
        return resultats
    
    def analyser_deliberation(self, deliberation: dict) -> Optional[Opportunite]:
        """Analyse une délibération pour détecter un projet chaufferie"""
        texte_complet = f"{deliberation.get('titre', '')} {deliberation.get('contenu', '')}".lower()
        
        # Chercher les mots clés
        mots_trouves = []
        for mot in MOTS_CLES_PRIORITAIRES:
            if mot.lower() in texte_complet:
                mots_trouves.append(mot)
        
        for mot in MOTS_CLES_SECONDAIRES:
            if mot.lower() in texte_complet:
                mots_trouves.append(mot)
        
        # Si pas de mots clés chaufferie, ignorer
        if not mots_trouves:
            return None
        
        # Déterminer confiance
        nb_prioritaires = sum(1 for m in mots_trouves if m in MOTS_CLES_PRIORITAIRES)
        if nb_prioritaires >= 2:
            confiance = 'forte'
        elif nb_prioritaires >= 1:
            confiance = 'moyenne'
        else:
            confiance = 'faible'
        
        # Extraire montant si présent
        montant = None
        patterns_montant = [
            r'(\d+[\s\.]?\d*)\s*€',
            r'(\d+[\s\.]?\d*)\s*EUR',
            r'montant de (\d+[\s\.]?\d*)',
            r'crédit de (\d+[\s\.]?\d*)'
        ]
        for pattern in patterns_montant:
            match = re.search(pattern, texte_complet, re.IGNORECASE)
            if match:
                montant_str = match.group(1).replace(' ', '').replace('.', '')
                try:
                    montant_int = int(montant_str)
                    if montant_int > 10000:  # Ignorer les petits montants
                        montant = f"{montant_int:,.0f} €".replace(',', ' ')
                        break
                except:
                    pass
        
        return Opportunite(
            commune=deliberation['commune'],
            departement=deliberation.get('departement', 'Non spécifié'),
            date_delib=deliberation.get('date', 'Non datée'),
            titre=deliberation.get('titre', 'Sans titre'),
            mots_cles_trouves=mots_trouves,
            url_source=deliberation.get('url', ''),
            confiance=confiance,
            montant_estime=montant,
            description=deliberation.get('contenu', '')[:200] + '...'
        )
    
    def lancer_veille(self, jours_retro: int = 180) -> List[Opportunite]:
        """Lance la veille sur toutes les communes ciblées"""
        print(f"🚀 Lancement de la veille - {len([c for deps in COMMUNES_CIBLEES.values() for c in deps])} communes à analyser")
        print(f"📅 Recherche sur les {jours_retro} derniers jours")
        print("=" * 80)
        
        opportunites = []
        
        for departement, communes in COMMUNES_CIBLEES.items():
            print(f"\n📍 Département: {departement}")
            
            for commune in communes:
                time.sleep(0.5)  # Respecter les serveurs
                
                # Scraper les délibérations
                delibs = self.scraper_deliberations_mairie(commune, departement)
                
                # Analyser chaque délibération
                for delib in delibs:
                    opp = self.analyser_deliberation(delib)
                    if opp:
                        opportunites.append(opp)
                        print(f"  🔥 {opp.confiance.upper()}: {opp.commune} - {opp.titre[:50]}...")
        
        # Trier par confiance
        opportunites.sort(key=lambda x: {'forte': 0, 'moyenne': 1, 'faible': 2}[x.confiance])
        
        return opportunites
    
    def generer_rapport(self, opportunites: List[Opportunite], format: str = 'json') -> str:
        """Génère un rapport des opportunités détectées"""
        
        if format == 'json':
            data = []
            for opp in opportunites:
                data.append({
                    'commune': opp.commune,
                    'departement': opp.departement,
                    'date': opp.date_delib,
                    'titre': opp.titre,
                    'confiance': opp.confiance,
                    'montant': opp.montant_estime,
                    'mots_cles': opp.mots_cles_trouves,
                    'description': opp.description
                })
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        elif format == 'markdown':
            md = "# 🔥 Opportunités Chaufferie Biomasse Détectées\n\n"
            md += f"*Généré le {datetime.now().strftime('%d/%m/%Y')}*\n\n"
            
            for i, opp in enumerate(opportunites, 1):
                emoji = {'forte': '🔴', 'moyenne': '🟠', 'faible': '🟢'}[opp.confiance]
                md += f"## {emoji} {i}. {opp.commune} ({opp.departement})\n\n"
                md += f"**Confiance:** {opp.confiance.upper()}\n\n"
                md += f"**Date délibération:** {opp.date_delib}\n\n"
                md += f"**Titre:** {opp.titre}\n\n"
                if opp.montant_estime:
                    md += f"**Montant estimé:** {opp.montant_estime}\n\n"
                md += f"**Mots-clés détectés:** {', '.join(opp.mots_cles_trouves)}\n\n"
                md += f"**Description:** {opp.description}\n\n"
                md += "---\n\n"
            
            return md
        
        return ""
    
    def exporter_contacts_commerciaux(self, opportunites: List[Opportunite]) -> List[dict]:
        """Prépare une liste de contacts pour prospection"""
        contacts = []
        for opp in opportunites:
            if opp.confiance in ['forte', 'moyenne']:
                contacts.append({
                    'commune': opp.commune,
                    'departement': opp.departement,
                    'priorite': 'HAUTE' if opp.confiance == 'forte' else 'MOYENNE',
                    'prochaine_action': 'Contacter directeur technique ou direction générale',
                    'argumentaire': f"Projet {', '.join(opp.mots_cles_trouves[:2])} identifié. Anticiper l'AO.",
                    'montant_potentiel': opp.montant_estime
                })
        return contacts


def main():
    """Point d'entrée principal"""
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║  POC VEILLE CHAUFFERIE BIOMASSE - AUVERGNE                      ║
    ║  Détection précoce des projets avant publication BOAMP          ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    veille = VeilleChaufferie()
    
    # Lancer la veille
    opportunites = veille.lancer_veille(jours_retro=180)
    
    # Afficher résultats
    print("\n" + "=" * 80)
    print(f"📊 RÉSULTATS: {len(opportunites)} opportunité(s) détectée(s)")
    print("=" * 80)
    
    # Stats
    stats = {'forte': 0, 'moyenne': 0, 'faible': 0}
    for opp in opportunites:
        stats[opp.confiance] += 1
    
    print(f"\n🔴 Forte confiance: {stats['forte']}")
    print(f"🟠 Moyenne confiance: {stats['moyenne']}")
    print(f"🟢 Faible confiance: {stats['faible']}")
    
    # Générer rapports
    if opportunites:
        print("\n📄 Génération des rapports...")
        
        # Rapport Markdown
        rapport_md = veille.generer_rapport(opportunites, format='markdown')
        with open('rapport_opportunites.md', 'w', encoding='utf-8') as f:
            f.write(rapport_md)
        print("  ✅ rapport_opportunites.md créé")
        
        # Export JSON
        rapport_json = veille.generer_rapport(opportunites, format='json')
        with open('opportunites.json', 'w', encoding='utf-8') as f:
            f.write(rapport_json)
        print("  ✅ opportunites.json créé")
        
        # Liste contacts commerciaux
        contacts = veille.exporter_contacts_commerciaux(opportunites)
        with open('contacts_commerciaux.json', 'w', encoding='utf-8') as f:
            json.dump(contacts, indent=2, fp=f, ensure_ascii=False)
        print("  ✅ contacts_commerciaux.json créé")
        
        # Afficher les meilleures opportunités
        print("\n" + "=" * 80)
        print("🎯 TOP OPPORTUNITÉS À CONTACTER EN PRIORITÉ:")
        print("=" * 80)
        for i, opp in enumerate([o for o in opportunites if o.confiance == 'forte'][:3], 1):
            print(f"\n{i}. {opp.commune} ({opp.departement})")
            print(f"   📅 {opp.date_delib}")
            print(f"   💰 {opp.montant_estime or 'Montant non précisé'}")
            print(f"   📝 {opp.titre}")
            print(f"   🔑 {', '.join(opp.mots_cles_trouves[:3])}")
    
    else:
        print("\n🤷 Aucune opportunité détectée (ceci est une simulation pour le POC)")
    
    print("\n" + "=" * 80)
    print("💡 PROCHAINES ÉTAPES POUR PRODUCTION:")
    print("=" * 80)
    print("1. Connecteur API pour récupérer les vraies délibérations (API Etalab/OpenData)")
    print("2. Scraping des sites de mairies avec BeautifulSoup + Playwright")
    print("3. Parsing PDF des délibérations avec PyPDF2/pdfplumber")
    print("4. Alertes automatiques (webhook/email/Notion)")
    print("5. Dashboard Streamlit pour visualisation")
    print("=" * 80)


if __name__ == '__main__':
    main()
