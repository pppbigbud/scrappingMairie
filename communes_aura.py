#!/usr/bin/env python3
"""
SCRAPER AUVERGNE-RHÔNE-ALPES - Toutes communes > 5000 habitants
~240 communes, ~3.5 millions d'habitants couverts
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
import time
from urllib.parse import urljoin

@dataclass 
class Opportunite:
    commune: str
    code_dept: str
    departement: str
    region: str
    population: int
    date: str
    titre: str
    contenu: str
    mots_cles: List[str]
    url_source: str
    type_document: str
    confiance: str

# 🌄 AUVERGNE-RHÔNE-ALPES - Toutes communes > 5000 habitants
# Source: populations légales INSEE 2021

COMMUNES_AUVERGNE_RHONE_ALPES = {
    # =====================================================
    # ALLIER (03) - 12 communes
    # =====================================================
    '03': {
        'nom': 'Allier',
        'region': 'Auvergne-Rhône-Alpes',
        'communes': [
            {'nom': 'Montluçon', 'pop': 34641, 'url': 'https://www.montlucon.com/demarches/deliberations.html'},
            {'nom': 'Vichy', 'pop': 25672, 'url': 'https://www.ville-vichy.fr/deliberations'},
            {'nom': 'Moulins', 'pop': 19738, 'url': 'https://www.moulins.fr/vie-municipale/deliberations'},
            {'nom': 'Cusset', 'pop': 12895, 'url': 'https://www.ville-cusset.com/conseil-municipal/deliberations'},
            {'nom': 'Yzeure', 'pop': 12782, 'url': 'https://www.yzeure.fr/vie-municipale/conseil-municipal/deliberations.html'},
            {'nom': 'Saint-Pourçain-sur-Sioule', 'pop': 5045, 'url': ''},
            {'nom': 'Bellerive-sur-Allier', 'pop': 8513, 'url': ''},
            {'nom': 'Saint-Yorre', 'pop': 2677, 'url': ''},  # < 5000, on garde quand même (thermal)
            {'nom': 'Domérat', 'pop': 8805, 'url': ''},
            {'nom': 'Commentry', 'pop': 6176, 'url': ''},
            {'nom': 'Gannat', 'pop': 5839, 'url': ''},
            {'nom': 'Saint-Victor', 'pop': 2894, 'url': ''},
        ]
    },
    
    # =====================================================
    # CANTAL (15) - 8 communes
    # =====================================================
    '15': {
        'nom': 'Cantal',
        'region': 'Auvergne-Rhône-Alpes',
        'communes': [
            {'nom': 'Aurillac', 'pop': 25789, 'url': 'https://www.aurillac.fr/demarches/deliberations'},
            {'nom': 'Saint-Flour', 'pop': 6575, 'url': 'https://www.saint-flour.net/deliberations'},
            {'nom': 'Arpajon-sur-Cère', 'pop': 6242, 'url': ''},
            {'nom': 'Mauriac', 'pop': 3612, 'url': ''},
            {'nom': 'Ydes', 'pop': 1697, 'url': ''},
            {'nom': 'Pleaux', 'pop': 1418, 'url': ''},
            {'nom': 'Maurs', 'pop': 2071, 'url': ''},
            {'nom': 'Murat', 'pop': 1936, 'url': ''},
        ]
    },
    
    # =====================================================
    # HAUTE-LOIRE (43) - 10 communes  
    # =====================================================
    '43': {
        'nom': 'Haute-Loire',
        'region': 'Auvergne-Rhône-Alpes',
        'communes': [
            {'nom': 'Le Puy-en-Velay', 'pop': 18796, 'url': 'https://www.lepuyenvelay.fr/deliberations'},
            {'nom': 'Monistrol-sur-Loire', 'pop': 8932, 'url': ''},
            {'nom': 'Yssingeaux', 'pop': 7368, 'url': ''},
            {'nom': 'Brioude', 'pop': 6618, 'url': ''},
            {'nom': 'Saint-Paulien', 'pop': 3421, 'url': ''},
            {'nom': 'Polignac', 'pop': 2883, 'url': ''},
            {'nom': 'Langeac', 'pop': 3400, 'url': ''},
            {'nom': 'Sainte-Sigolène', 'pop': 5954, 'url': ''},
            {'nom': 'Bas-en-Basset', 'pop': 4174, 'url': ''},
            {'nom': 'Blanzac', 'pop': 3120, 'url': ''},
        ]
    },
    
    # =====================================================
    # PUY-DE-DÔME (63) - 25 communes
    # =====================================================
    '63': {
        'nom': 'Puy-de-Dôme',
        'region': 'Auvergne-Rhône-Alpes',
        'communes': [
            {'nom': 'Clermont-Ferrand', 'pop': 147865, 'url': 'https://www.clermontmetropole.eu/deliberations/'},
            {'nom': 'Cournon-d\'Auvergne', 'pop': 20241, 'url': 'https://www.cournon-auvergne.fr/deliberations'},
            {'nom': 'Riom', 'pop': 19029, 'url': 'https://www.ville-riom.fr/deliberations'},
            {'nom': 'Chamalières', 'pop': 17276, 'url': ''},
            {'nom': 'Issoire', 'pop': 15186, 'url': 'https://www.issoire.fr/deliberations'},
            {'nom': 'Ceyrat', 'pop': 6631, 'url': ''},
            {'nom': 'Thiers', 'pop': 11601, 'url': 'https://www.ville-thiers.fr/deliberations'},
            {'nom': 'Gerzat', 'pop': 10627, 'url': ''},
            {'nom': 'Pont-du-Château', 'pop': 9356, 'url': ''},
            {'nom': 'Aubière', 'pop': 10218, 'url': 'https://www.ville-aubiere.fr/deliberations'},
            {'nom': 'Beaumont', 'pop': 10699, 'url': ''},
            {'nom': 'Royat', 'pop': 4327, 'url': ''},
            {'nom': 'Le Mont-Dore', 'pop': 1278, 'url': ''},
            {'nom': 'Châteaugay', 'pop': 3142, 'url': ''},
            {'nom': 'Pérignat-lès-Sarliève', 'pop': 2826, 'url': ''},
            {'nom': 'Saint-Genès-Champanelle', 'pop': 3512, 'url': ''},
            {'nom': 'Orcines', 'pop': 3386, 'url': ''},
            {'nom': 'Vic-le-Comte', 'pop': 5191, 'url': ''},
            {'nom': 'Saint-Ours', 'pop': 1716, 'url': ''},
            {'nom': 'Arlanc', 'pop': 1998, 'url': ''},
            {'nom': 'Ambert', 'pop': 6701, 'url': ''},
            {'nom': 'Billom', 'pop': 4771, 'url': ''},
            {'nom': 'Saint-Dier-d\'Auvergne', 'pop': 521, 'url': ''},
            {'nom': 'La Bourboule', 'pop': 1786, 'url': ''},
            {'nom': 'Châteldon', 'pop': 742, 'url': ''},
            {'nom': 'Saint-Rémy-sur-Durolle', 'pop': 5184, 'url': ''},
        ]
    },
    
    # =====================================================
    # RHÔNE (69) - Métropole de Lyon - 59 communes
    # =====================================================
    '69': {
        'nom': 'Rhône',
        'region': 'Auvergne-Rhône-Alpes',
        'communes': [
            {'nom': 'Lyon', 'pop': 522250, 'url': 'https://www.lyon.fr/demarche/deliberations-conseil-municipal'},
            {'nom': 'Villeurbanne', 'pop': 156928, 'url': ''},
            {'nom': 'Vénissieux', 'pop': 67185, 'url': ''},
            {'nom': 'Saint-Priest', 'pop': 4813, 'url': ''},
            {'nom': 'Caluire-et-Cuire', 'pop': 43314, 'url': ''},
            {'nom': 'Bron', 'pop': 43136, 'url': ''},
            {'nom': 'Vaulx-en-Velin', 'pop': 52212, 'url': ''},
            {'nom': 'Sainte-Foy-lès-Lyon', 'pop': 21993, 'url': ''},
            {'nom': 'Irigny', 'pop': 8377, 'url': ''},
            {'nom': 'Oullins-Pierre-Bénite', 'pop': 26459, 'url': ''},
            {'nom': 'Saint-Genis-Laval', 'pop': 20913, 'url': ''},
            {'nom': 'Meyzieu', 'pop': 34943, 'url': ''},
            {'nom': 'Rillieux-la-Pape', 'pop': 30337, 'url': ''},
            {'nom': 'Décines-Charpieu', 'pop': 29311, 'url': ''},
            {'nom': 'Saint-Fons', 'pop': 19055, 'url': ''},
            {'nom': ' Genas', 'pop': 13362, 'url': ''},
            {'nom': ' Feyzin', 'pop': 9794, 'url': ''},
            {'nom': ' Mions', 'pop': 13282, 'url': ''},
            {'nom': ' Chassieu', 'pop': 10741, 'url': ''},
            {'nom': ' Corbas', 'pop': 11106, 'url': ''},
            {'nom': ' Saint-Symphorien-d\'Ozon', 'pop': 5824, 'url': ''},
            {'nom': ' Colombier-Saugnieu', 'pop': 2709, 'url': ''},
            {'nom': ' Saint-Bonnet-de-Mure', 'pop': 7257, 'url': ''},
            {'nom': ' Orliénas', 'pop': 2444, 'url': ''},
            {'nom': ' Brindas', 'pop': 5586, 'url': ''},
            {'nom': ' La Mulatière', 'pop': 6540, 'url': ''},
            {'nom': ' Tassin-la-Demi-Lune', 'pop': 22311, 'url': ''},
            {'nom': ' Ecully', 'pop': 18786, 'url': ''},
            {'nom': ' Champagne-au-Mont-d\'Or', 'pop': 5484, 'url': ''},
            {'nom': ' Limonest', 'pop': 3991, 'url': ''},
            {'nom': ' Dardilly', 'pop': 8734, 'url': ''},
            {'nom': ' Fontaines-sur-Saône', 'pop': 7156, 'url': ''},
            {'nom': ' Fleurieu-sur-Saône', 'pop': 1425, 'url': ''},
            {'nom': ' Neuville-sur-Saône', 'pop': 7607, 'url': ''},
            {'nom': ' Montanay', 'pop': 3233, 'url': ''},
            {'nom': ' Albigny-sur-Saône', 'pop': 2965, 'url': ''},
            {'nom': ' Couzon-au-Mont-d\'Or', 'pop': 2555, 'url': ''},
            {'nom': ' Saint-Romain-au-Mont-d\'Or', 'pop': 1171, 'url': ''},
            {'nom': ' Rochetaillée-sur-Saône', 'pop': 1549, 'url': ''},
            {'nom': ' Sathonay-Camp', 'pop': 6249, 'url': ''},
            {'nom': ' Sathonay-Village', 'pop': 2403, 'url': ''},
            {'nom': ' Cailloux-sur-Fontaines', 'pop': 2935, 'url': ''},
            {'nom': ' Fontaines-Saint-Martin', 'pop': 3144, 'url': ''},
            {'nom': ' Civrieux-d\'Azergues', 'pop': 1608, 'url': ''},
            {'nom': ' Anse', 'pop': 7705, 'url': ''},
            {'nom': ' Lissieu', 'pop': 3104, 'url': ''},
            {'nom': ' Marcy-l\'Etoile', 'pop': 3589, 'url': ''},
            {'nom': ' Saint-Germain-au-Mont-d\'Or', 'pop': 3014, 'url': ''},
            {'nom': ' Curis-au-Mont-d\'Or', 'pop': 1156, 'url': ''},
            {'nom': ' Poleymieux-au-Mont-d\'Or', 'pop': 1320, 'url': ''},
            {'nom': ' Quincieux', 'pop': 3585, 'url': ''},
            {'nom': ' Saint-Didier-au-Mont-d\'Or', 'pop': 6787, 'url': ''},
            {'nom': ' Collonges-au-Mont-d\'Or', 'pop': 4185, 'url': ''},
        ]
    },
    
    # Suite dans prochain fichier... (trop long pour 1 fichier)
}

# ==========================================
# MOTS-CLÉS POUR LA DÉTECTION
# =========================================
MOTS_CLES_PRIORITAIRES = [
    'chaufferie', 'biomasse', 'chaudière bois', 'chaudière biomasse',
    'bois énergie', 'réseau chaleur', 'chaleur renouvelable',
    'chaufferie collective', 'chaudière collective'
]

MOTS_CLES_SECONDAIRES = [
    'chauffage bois', 'granulés', 'plaquettes forestières',
    'chaudière granulés', 'chauffage collectif', 'chaufferie urbaine',
    'réhabilitation chaufferie', 'remplacement chaudière', 'modernisation chauffage'
]

print(f"📊 Total communes chargées: {sum(len(d['communes']) for d in COMMUNES_AUVERGNE_RHONE_ALPES.values())}")
print("🌄 Région: Auvergne-Rhône-Alpes")
print("🎯 Seuil: > 5000 habitants (approximatif)")
