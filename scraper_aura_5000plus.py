#!/usr/bin/env python3
"""
SCRAPER AURA - TOUTES COMMUNES 5000+ HABITANTS
Region Auvergne-Rhône-Alpes complète
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
from urllib.parse import urljoin
import sys
import concurrent.futures
from threading import Lock

sys.stdout.reconfigure(line_buffering=True)

@dataclass
class ProjetChaufferie:
    commune: str
    departement: str
    source_type: str
    titre: str
    extrait: str
    mots_cles: List[str]
    phase: str
    url: str
    contact: Optional[str] = None
    population: Optional[int] = None

# MOTS-CLÉS CHAUFFERIE
MOTS_CLES = [
    'chaufferie', 'chaudière', 'biomasse', 'bois énergie', 'bois-énergie',
    'granulés', 'plaquettes', 'pellets', 'fioul', 'fuel',
    'réseau de chaleur', 'réseau chaleur', 'chauffage collectif',
    'géothermie', 'pompe à chaleur', 'PAC'
]

# MOTS CONTEXTE
CONTEXTE = [
    'projet', 'étude', 'remplacement', 'modernisation', 'rénovation',
    'transition énergétique', 'plan climat', 'subvention', 'mandat'
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

# COMMUNES AURA 5000+ habitants (données INSEE 2021)
# 12 départements: 01, 03, 07, 15, 26, 38, 42, 43, 63, 69, 73, 74
COMMUNES_AURA_5000 = [
    # === AIN (01) ===
    {'commune': 'Bourg-en-Bresse', 'dept': '01', 'url': 'https://www.bourgenbresse.fr', 'pop': 41365},
    {'commune': 'Oyonnax', 'dept': '01', 'url': 'https://www.oyonnax.fr', 'pop': 22559},
    {'commune': 'Ambérieu-en-Bugey', 'dept': '01', 'url': 'https://www.amberieu-en-bugey.fr', 'pop': 14127},
    {'commune': 'Gex', 'dept': '01', 'url': 'https://www.ville-gex.fr', 'pop': 13459},
    {'commune': 'Bellegarde-sur-Valserine', 'dept': '01', 'url': 'https://www.ville-bellegarde01.fr', 'pop': 12269},
    {'commune': 'Miribel', 'dept': '01', 'url': 'https://www.miribel.fr', 'pop': 10164},
    {'commune': 'Ferney-Voltaire', 'dept': '01', 'url': 'https://www.ferney-voltaire.fr', 'pop': 10081},
    {'commune': 'Saint-Genis-Pouilly', 'dept': '01', 'url': 'https://www.saint-genis-pouilly.fr', 'pop': 12899},
    {'commune': 'Belley', 'dept': '01', 'url': 'https://www.belley.fr', 'pop': 9215},
    {'commune': 'Divonne-les-Bains', 'dept': '01', 'url': 'https://www.divonne.fr', 'pop': 9667},
    {'commune': 'Trévoux', 'dept': '01', 'url': 'https://www.mairie-trevoux.fr', 'pop': 7113},
    {'commune': 'Montluel', 'dept': '01', 'url': 'https://www.montluel.fr', 'pop': 7266},
    {'commune': 'Meximieux', 'dept': '01', 'url': 'https://www.meximieux.fr', 'pop': 7718},
    {'commune': 'Villars-les-Dombes', 'dept': '01', 'url': 'https://www.villars-les-dombes.fr', 'pop': 5800},
    {'commune': 'Châtillon-sur-Chalaronne', 'dept': '01', 'url': 'https://www.chatillon-sur-chalaronne.fr', 'pop': 5200},
    {'commune': 'Lagnieu', 'dept': '01', 'url': 'https://www.lagnieu.fr', 'pop': 7200},
    {'commune': 'Prévessin-Moëns', 'dept': '01', 'url': 'https://www.prevessin-moens.fr', 'pop': 8800},
    {'commune': 'Nivigne-et-Suran', 'dept': '01', 'url': 'https://www.nivigne-et-suran.fr', 'pop': 2500},  # Gardé car résultat confirmé
    
    # === ALLIER (03) ===
    {'commune': 'Montluçon', 'dept': '03', 'url': 'https://www.ville-montlucon.fr', 'pop': 36240},
    {'commune': 'Vichy', 'dept': '03', 'url': 'https://www.ville-vichy.fr', 'pop': 24980},
    {'commune': 'Moulins', 'dept': '03', 'url': 'https://www.moulins.fr', 'pop': 19837},
    {'commune': 'Cusset', 'dept': '03', 'url': 'https://www.ville-cusset.com', 'pop': 13351},
    {'commune': 'Yzeure', 'dept': '03', 'url': 'https://www.yzeure.com', 'pop': 12800},
    {'commune': 'Désertines', 'dept': '03', 'url': 'https://www.desertines03.fr', 'pop': 8400},
    {'commune': 'Bellerive-sur-Allier', 'dept': '03', 'url': 'https://www.ville-bellerive.fr', 'pop': 8700},
    {'commune': 'Domérat', 'dept': '03', 'url': 'https://www.domerat.fr', 'pop': 8900},
    {'commune': 'Commentry', 'dept': '03', 'url': 'https://www.commentry.fr', 'pop': 6200},
    {'commune': 'Gannat', 'dept': '03', 'url': 'https://www.ville-gannat.fr', 'pop': 5900},
    
    # === ARDÈCHE (07) ===
    {'commune': 'Annonay', 'dept': '07', 'url': 'https://www.annonay.fr', 'pop': 16600},
    {'commune': 'Aubenas', 'dept': '07', 'url': 'https://www.aubenas.fr', 'pop': 12500},
    {'commune': 'Guilherand-Granges', 'dept': '07', 'url': 'https://www.guilherandgranges.fr', 'pop': 11400},
    {'commune': 'Tournon-sur-Rhône', 'dept': '07', 'url': 'https://www.tournon-sur-rhone.fr', 'pop': 11200},
    {'commune': 'Privas', 'dept': '07', 'url': 'https://www.privas.fr', 'pop': 8500},
    {'commune': 'Le Teil', 'dept': '07', 'url': 'https://www.leteil.fr', 'pop': 8800},
    {'commune': 'Bourg-Saint-Andéol', 'dept': '07', 'url': 'https://www.bourg-saint-andeol.fr', 'pop': 7200},
    {'commune': 'Davézieux', 'dept': '07', 'url': 'https://www.davezieux.fr', 'pop': 6100},
    
    # === CANTAL (15) ===
    {'commune': 'Aurillac', 'dept': '15', 'url': 'https://www.aurillac.fr', 'pop': 25500},
    {'commune': 'Saint-Flour', 'dept': '15', 'url': 'https://www.saint-flour.fr', 'pop': 6600},
    {'commune': 'Arpajon-sur-Cère', 'dept': '15', 'url': 'https://www.arpajon-sur-cere.fr', 'pop': 6100},
    
    # === DRÔME (26) ===
    {'commune': 'Valence', 'dept': '26', 'url': 'https://www.valence.fr', 'pop': 65000},
    {'commune': 'Montélimar', 'dept': '26', 'url': 'https://www.montelimar.fr', 'pop': 40000},
    {'commune': 'Romans-sur-Isère', 'dept': '26', 'url': 'https://www.ville-romans.fr', 'pop': 34000},
    {'commune': 'Bourg-lès-Valence', 'dept': '26', 'url': 'https://www.bourg-les-valence.fr', 'pop': 20500},
    {'commune': 'Pierrelatte', 'dept': '26', 'url': 'https://www.pierrelatte.fr', 'pop': 14000},
    {'commune': 'Portes-lès-Valence', 'dept': '26', 'url': 'https://www.porteslesvalence.fr', 'pop': 10500},
    {'commune': 'Crest', 'dept': '26', 'url': 'https://www.mairie-crest.fr', 'pop': 8500},
    {'commune': 'Livron-sur-Drôme', 'dept': '26', 'url': 'https://www.livron.fr', 'pop': 9300},
    {'commune': 'Loriol-sur-Drôme', 'dept': '26', 'url': 'https://www.loriol-sur-drome.fr', 'pop': 6900},
    {'commune': 'Saint-Vallier', 'dept': '26', 'url': 'https://www.saint-vallier.fr', 'pop': 6400},
    {'commune': 'Die', 'dept': '26', 'url': 'https://www.mairie-die.fr', 'pop': 5000},
    {'commune': 'Nyons', 'dept': '26', 'url': 'https://www.nyons.fr', 'pop': 6700},
    {'commune': 'Tain-l\'Hermitage', 'dept': '26', 'url': 'https://www.ville-tain-hermitage.fr', 'pop': 6300},
    
    # === ISÈRE (38) ===
    {'commune': 'Grenoble', 'dept': '38', 'url': 'https://www.grenoble.fr', 'pop': 158000},
    {'commune': 'Saint-Martin-d\'Hères', 'dept': '38', 'url': 'https://www.saintmartindheres.fr', 'pop': 38000},
    {'commune': 'Échirolles', 'dept': '38', 'url': 'https://www.echirolles.fr', 'pop': 36500},
    {'commune': 'Vienne', 'dept': '38', 'url': 'https://www.vienne.fr', 'pop': 30000},
    {'commune': 'Bourgoin-Jallieu', 'dept': '38', 'url': 'https://www.bourgoinjallieu.fr', 'pop': 28500},
    {'commune': 'Fontaine', 'dept': '38', 'url': 'https://www.fontaine38.fr', 'pop': 23000},
    {'commune': 'Voiron', 'dept': '38', 'url': 'https://www.ville-voiron.fr', 'pop': 21000},
    {'commune': 'Villefontaine', 'dept': '38', 'url': 'https://www.villefontaine.fr', 'pop': 19500},
    {'commune': 'Meylan', 'dept': '38', 'url': 'https://www.meylan.fr', 'pop': 18000},
    {'commune': 'Saint-Égrève', 'dept': '38', 'url': 'https://www.saint-egreve.fr', 'pop': 17000},
    {'commune': 'L\'Isle-d\'Abeau', 'dept': '38', 'url': 'https://www.isle-dabeau.fr', 'pop': 16500},
    {'commune': 'Le Pont-de-Claix', 'dept': '38', 'url': 'https://www.pontdeclaix.fr', 'pop': 11500},
    {'commune': 'Seyssinet-Pariset', 'dept': '38', 'url': 'https://www.seyssinet-pariset.fr', 'pop': 12000},
    {'commune': 'Sassenage', 'dept': '38', 'url': 'https://www.sassenage.fr', 'pop': 11600},
    {'commune': 'Crolles', 'dept': '38', 'url': 'https://www.crolles.fr', 'pop': 8500},
    {'commune': 'La Verpillière', 'dept': '38', 'url': 'https://www.laverpilliere.fr', 'pop': 7200},
    {'commune': 'Saint-Martin-le-Vinoux', 'dept': '38', 'url': 'https://www.saint-martin-le-vinoux.fr', 'pop': 5800},
    {'commune': 'Pontcharra', 'dept': '38', 'url': 'https://www.pontcharra.fr', 'pop': 7500},
    {'commune': 'Vizille', 'dept': '38', 'url': 'https://www.ville-vizille.fr', 'pop': 7800},
    {'commune': 'Charvieu-Chavagneux', 'dept': '38', 'url': 'https://www.charvieu-chavagneux.fr', 'pop': 9000},
    {'commune': 'Voreppe', 'dept': '38', 'url': 'https://www.voreppe.fr', 'pop': 10000},
    {'commune': 'Claix', 'dept': '38', 'url': 'https://www.ville-claix.fr', 'pop': 8600},
    {'commune': 'Tullins', 'dept': '38', 'url': 'https://www.ville-tullins.fr', 'pop': 7800},
    {'commune': 'Moirans', 'dept': '38', 'url': 'https://www.moirans.fr', 'pop': 8300},
    {'commune': 'Roussillon', 'dept': '38', 'url': 'https://www.ville-roussillon.fr', 'pop': 8600},
    {'commune': 'Domène', 'dept': '38', 'url': 'https://www.domene.fr', 'pop': 6700},
    {'commune': 'Saint-Marcellin', 'dept': '38', 'url': 'https://www.saint-marcellin.fr', 'pop': 7800},
    {'commune': 'Villard-Bonnot', 'dept': '38', 'url': 'https://www.villardbonnot.fr', 'pop': 7000},
    {'commune': 'Heyrieux', 'dept': '38', 'url': 'https://www.heyrieux.fr', 'pop': 5400},
    {'commune': 'La Tour-du-Pin', 'dept': '38', 'url': 'https://www.ville-la-tour-du-pin.fr', 'pop': 8300},
    
    # === LOIRE (42) ===
    {'commune': 'Saint-Étienne', 'dept': '42', 'url': 'https://www.saint-etienne.fr', 'pop': 174000},
    {'commune': 'Roanne', 'dept': '42', 'url': 'https://www.roanne.fr', 'pop': 35000},
    {'commune': 'Saint-Chamond', 'dept': '42', 'url': 'https://www.saint-chamond.fr', 'pop': 35000},
    {'commune': 'Firminy', 'dept': '42', 'url': 'https://www.ville-firminy.fr', 'pop': 17500},
    {'commune': 'Montbrison', 'dept': '42', 'url': 'https://www.ville-montbrison.fr', 'pop': 16000},
    {'commune': 'Rive-de-Gier', 'dept': '42', 'url': 'https://www.rive-de-gier.fr', 'pop': 16000},
    {'commune': 'Le Chambon-Feugerolles', 'dept': '42', 'url': 'https://www.lechambon.fr', 'pop': 12800},
    {'commune': 'Saint-Just-Saint-Rambert', 'dept': '42', 'url': 'https://www.stjust-strambert.fr', 'pop': 15500},
    {'commune': 'Andrézieux-Bouthéon', 'dept': '42', 'url': 'https://www.andrezieux-boutheon.fr', 'pop': 9800},
    {'commune': 'Riorges', 'dept': '42', 'url': 'https://www.riorges.fr', 'pop': 10800},
    {'commune': 'La Ricamarie', 'dept': '42', 'url': 'https://www.laricamarie.fr', 'pop': 8000},
    {'commune': 'Sorbiers', 'dept': '42', 'url': 'https://www.sorbiers.fr', 'pop': 8000},
    {'commune': 'Unieux', 'dept': '42', 'url': 'https://www.unieux.fr', 'pop': 8500},
    {'commune': 'Saint-Priest-en-Jarez', 'dept': '42', 'url': 'https://www.saint-priest-en-jarez.fr', 'pop': 6200},
    {'commune': 'Mably', 'dept': '42', 'url': 'https://www.mably.fr', 'pop': 7800},
    {'commune': 'Veauche', 'dept': '42', 'url': 'https://www.veauche.fr', 'pop': 9000},
    {'commune': 'La Talaudière', 'dept': '42', 'url': 'https://www.la-talaudiere.fr', 'pop': 7000},
    {'commune': 'L\'Étrat', 'dept': '42', 'url': 'https://www.letrat.fr', 'pop': 5500},
    {'commune': 'Villars', 'dept': '42', 'url': 'https://www.villars42.fr', 'pop': 8800},
    {'commune': 'Feurs', 'dept': '42', 'url': 'https://www.feurs.fr', 'pop': 8000},
    
    # === HAUTE-LOIRE (43) ===
    {'commune': 'Le Puy-en-Velay', 'dept': '43', 'url': 'https://www.lepuyenvelay.fr', 'pop': 18700},
    {'commune': 'Monistrol-sur-Loire', 'dept': '43', 'url': 'https://www.monistrol-sur-loire.fr', 'pop': 9000},
    {'commune': 'Yssingeaux', 'dept': '43', 'url': 'https://www.yssingeaux.fr', 'pop': 7200},
    {'commune': 'Brioude', 'dept': '43', 'url': 'https://www.brioude.fr', 'pop': 6700},
    {'commune': 'Sainte-Sigolène', 'dept': '43', 'url': 'https://www.sainte-sigolene.fr', 'pop': 6200},
    {'commune': 'Aurec-sur-Loire', 'dept': '43', 'url': 'https://www.aurec-sur-loire.fr', 'pop': 5900},
    
    # === PUY-DE-DÔME (63) ===
    {'commune': 'Clermont-Ferrand', 'dept': '63', 'url': 'https://www.clermontferrand.fr', 'pop': 147000},
    {'commune': 'Cournon-d\'Auvergne', 'dept': '63', 'url': 'https://www.cournon-auvergne.fr', 'pop': 20000},
    {'commune': 'Riom', 'dept': '63', 'url': 'https://www.ville-riom.fr', 'pop': 19000},
    {'commune': 'Chamalières', 'dept': '63', 'url': 'https://www.ville-chamalieres.fr', 'pop': 17700},
    {'commune': 'Issoire', 'dept': '63', 'url': 'https://www.issoire.fr', 'pop': 14000},
    {'commune': 'Thiers', 'dept': '63', 'url': 'https://www.ville-thiers.fr', 'pop': 11800},
    {'commune': 'Beaumont', 'dept': '63', 'url': 'https://www.beaumont63.fr', 'pop': 11400},
    {'commune': 'Aubière', 'dept': '63', 'url': 'https://www.aubiere.fr', 'pop': 10400},
    {'commune': 'Gerzat', 'dept': '63', 'url': 'https://www.gerzat.fr', 'pop': 10000},
    {'commune': 'Romagnat', 'dept': '63', 'url': 'https://www.romagnat.fr', 'pop': 8500},
    {'commune': 'Pont-du-Château', 'dept': '63', 'url': 'https://www.pontduchateau.fr', 'pop': 11500},
    {'commune': 'Ceyrat', 'dept': '63', 'url': 'https://www.ceyrat.fr', 'pop': 6300},
    {'commune': 'Lempdes', 'dept': '63', 'url': 'https://www.ville-lempdes.fr', 'pop': 9000},
    {'commune': 'Ambert', 'dept': '63', 'url': 'https://www.ambert.fr', 'pop': 6700},
    {'commune': 'Mozac', 'dept': '63', 'url': 'https://www.mozac.fr', 'pop': 3800},
    {'commune': 'Clermont-Auvergne Métropole', 'dept': '63', 'url': 'https://www.clermontmetropole.eu', 'pop': 300000},
    
    # === RHÔNE (69) - hors Lyon Métropole ===
    {'commune': 'Villefranche-sur-Saône', 'dept': '69', 'url': 'https://www.villefranche.net', 'pop': 37000},
    {'commune': 'Tarare', 'dept': '69', 'url': 'https://www.tarare.fr', 'pop': 10800},
    {'commune': 'L\'Arbresle', 'dept': '69', 'url': 'https://www.larbresle.fr', 'pop': 6800},
    {'commune': 'Belleville-en-Beaujolais', 'dept': '69', 'url': 'https://www.belleville-en-beaujolais.fr', 'pop': 8200},
    {'commune': 'Givors', 'dept': '69', 'url': 'https://www.givors.fr', 'pop': 20500},
    {'commune': 'Gleizé', 'dept': '69', 'url': 'https://www.gleize.fr', 'pop': 8500},
    {'commune': 'Limas', 'dept': '69', 'url': 'https://www.limas.fr', 'pop': 5300},
    {'commune': 'Thizy-les-Bourgs', 'dept': '69', 'url': 'https://www.thizy-les-bourgs.fr', 'pop': 5400},
    
    # === LYON MÉTROPOLE (69) ===
    {'commune': 'Lyon', 'dept': '69', 'url': 'https://www.lyon.fr', 'pop': 522000},
    {'commune': 'Villeurbanne', 'dept': '69', 'url': 'https://www.villeurbanne.fr', 'pop': 152000},
    {'commune': 'Vénissieux', 'dept': '69', 'url': 'https://www.venissieux.fr', 'pop': 66000},
    {'commune': 'Saint-Priest', 'dept': '69', 'url': 'https://www.saint-priest.fr', 'pop': 47000},
    {'commune': 'Caluire-et-Cuire', 'dept': '69', 'url': 'https://www.caluire-et-cuire.fr', 'pop': 43000},
    {'commune': 'Bron', 'dept': '69', 'url': 'https://www.ville-bron.fr', 'pop': 42000},
    {'commune': 'Vaulx-en-Velin', 'dept': '69', 'url': 'https://www.vaulx-en-velin.net', 'pop': 52000},
    {'commune': 'Meyzieu', 'dept': '69', 'url': 'https://www.meyzieu.fr', 'pop': 34000},
    {'commune': 'Rillieux-la-Pape', 'dept': '69', 'url': 'https://www.rillieux-la-pape.fr', 'pop': 31000},
    {'commune': 'Décines-Charpieu', 'dept': '69', 'url': 'https://www.decines.fr', 'pop': 28000},
    {'commune': 'Oullins', 'dept': '69', 'url': 'https://www.ville-oullins.fr', 'pop': 26000},
    {'commune': 'Sainte-Foy-lès-Lyon', 'dept': '69', 'url': 'https://www.saintefoyleslyon.fr', 'pop': 22500},
    {'commune': 'Tassin-la-Demi-Lune', 'dept': '69', 'url': 'https://www.mairie-tassinlademilune.fr', 'pop': 22000},
    {'commune': 'Saint-Genis-Laval', 'dept': '69', 'url': 'https://www.saintgenislaval.fr', 'pop': 21000},
    {'commune': 'Écully', 'dept': '69', 'url': 'https://www.ecully.fr', 'pop': 18500},
    {'commune': 'Francheville', 'dept': '69', 'url': 'https://www.ville-francheville.fr', 'pop': 14500},
    {'commune': 'Mions', 'dept': '69', 'url': 'https://www.mions.fr', 'pop': 13500},
    {'commune': 'Pierre-Bénite', 'dept': '69', 'url': 'https://www.pierre-benite.fr', 'pop': 10600},
    {'commune': 'Corbas', 'dept': '69', 'url': 'https://www.ville-corbas.fr', 'pop': 12500},
    {'commune': 'Chassieu', 'dept': '69', 'url': 'https://www.chassieu.fr', 'pop': 10500},
    {'commune': 'Feyzin', 'dept': '69', 'url': 'https://www.ville-feyzin.fr', 'pop': 9800},
    {'commune': 'Dardilly', 'dept': '69', 'url': 'https://www.dardilly.fr', 'pop': 9200},
    {'commune': 'Champagne-au-Mont-d\'Or', 'dept': '69', 'url': 'https://www.champagne-au-mont-dor.fr', 'pop': 5500},
    {'commune': 'Irigny', 'dept': '69', 'url': 'https://www.irigny.fr', 'pop': 8800},
    {'commune': 'Saint-Fons', 'dept': '69', 'url': 'https://www.saint-fons.fr', 'pop': 18000},
    {'commune': 'Grigny', 'dept': '69', 'url': 'https://www.grigny69.fr', 'pop': 9500},
    {'commune': 'Neuville-sur-Saône', 'dept': '69', 'url': 'https://www.neuvillesursaone.fr', 'pop': 8000},
    
    # === SAVOIE (73) ===
    {'commune': 'Chambéry', 'dept': '73', 'url': 'https://www.chambery.fr', 'pop': 60000},
    {'commune': 'Aix-les-Bains', 'dept': '73', 'url': 'https://www.aixlesbains.fr', 'pop': 31000},
    {'commune': 'Albertville', 'dept': '73', 'url': 'https://www.albertville.fr', 'pop': 19000},
    {'commune': 'La Motte-Servolex', 'dept': '73', 'url': 'https://www.lamotteservolex.fr', 'pop': 12000},
    {'commune': 'Cognin', 'dept': '73', 'url': 'https://www.cognin.fr', 'pop': 6500},
    {'commune': 'Saint-Alban-Leysse', 'dept': '73', 'url': 'https://www.saint-alban-leysse.fr', 'pop': 6500},
    {'commune': 'Bourg-Saint-Maurice', 'dept': '73', 'url': 'https://www.bourgsaintmaurice.fr', 'pop': 7500},
    {'commune': 'Saint-Jean-de-Maurienne', 'dept': '73', 'url': 'https://www.saintjeandemaurienne.fr', 'pop': 7700},
    {'commune': 'Ugine', 'dept': '73', 'url': 'https://www.ugine.fr', 'pop': 7000},
    {'commune': 'La Ravoire', 'dept': '73', 'url': 'https://www.laravoire.fr', 'pop': 9000},
    {'commune': 'Challes-les-Eaux', 'dept': '73', 'url': 'https://www.challesleseaux.fr', 'pop': 5500},
    {'commune': 'Jacob-Bellecombette', 'dept': '73', 'url': 'https://www.jacob-bellecombette.fr', 'pop': 6000},
    
    # === HAUTE-SAVOIE (74) ===
    {'commune': 'Annecy', 'dept': '74', 'url': 'https://www.annecy.fr', 'pop': 130000},
    {'commune': 'Annemasse', 'dept': '74', 'url': 'https://www.annemasse.fr', 'pop': 36000},
    {'commune': 'Thonon-les-Bains', 'dept': '74', 'url': 'https://www.ville-thonon.fr', 'pop': 36000},
    {'commune': 'Cluses', 'dept': '74', 'url': 'https://www.cluses.fr', 'pop': 18000},
    {'commune': 'Sallanches', 'dept': '74', 'url': 'https://www.sallanches.fr', 'pop': 16500},
    {'commune': 'Bonneville', 'dept': '74', 'url': 'https://www.bonneville.fr', 'pop': 13000},
    {'commune': 'Gaillard', 'dept': '74', 'url': 'https://www.ville-gaillard.fr', 'pop': 12500},
    {'commune': 'Rumilly', 'dept': '74', 'url': 'https://www.ville-rumilly74.fr', 'pop': 15500},
    {'commune': 'La Roche-sur-Foron', 'dept': '74', 'url': 'https://www.larochesurforon.fr', 'pop': 12000},
    {'commune': 'Passy', 'dept': '74', 'url': 'https://www.passy-mont-blanc.fr', 'pop': 11500},
    {'commune': 'Évian-les-Bains', 'dept': '74', 'url': 'https://www.ville-evian.fr', 'pop': 9000},
    {'commune': 'Scionzier', 'dept': '74', 'url': 'https://www.scionzier.fr', 'pop': 8700},
    {'commune': 'Saint-Julien-en-Genevois', 'dept': '74', 'url': 'https://www.st-julien-en-genevois.fr', 'pop': 16000},
    {'commune': 'Ville-la-Grand', 'dept': '74', 'url': 'https://www.ville-la-grand.fr', 'pop': 8500},
    {'commune': 'Seynod', 'dept': '74', 'url': 'https://www.seynod.fr', 'pop': 20000},
    {'commune': 'Meythet', 'dept': '74', 'url': 'https://www.meythet.fr', 'pop': 9000},
    {'commune': 'Cran-Gevrier', 'dept': '74', 'url': 'https://www.cran-gevrier.fr', 'pop': 18000},
    {'commune': 'Publier', 'dept': '74', 'url': 'https://www.ville-publier.fr', 'pop': 7000},
    {'commune': 'Chamonix-Mont-Blanc', 'dept': '74', 'url': 'https://www.chamonix.fr', 'pop': 8900},
    {'commune': 'Cranves-Sales', 'dept': '74', 'url': 'https://www.cranves-sales.fr', 'pop': 6500},
    {'commune': 'Vetraz-Monthoux', 'dept': '74', 'url': 'https://www.vetraz-monthoux.fr', 'pop': 8000},
    {'commune': 'Faverges-Seythenex', 'dept': '74', 'url': 'https://www.faverges-seythenex.fr', 'pop': 8000},
    {'commune': 'Saint-Pierre-en-Faucigny', 'dept': '74', 'url': 'https://www.st-pierre-en-faucigny.fr', 'pop': 7500},
    {'commune': 'Marnaz', 'dept': '74', 'url': 'https://www.marnaz.fr', 'pop': 5800},
    {'commune': 'Sciez', 'dept': '74', 'url': 'https://www.sciez.fr', 'pop': 6200},
]

# Supprimer les doublons par URL
seen_urls = set()
COMMUNES_UNIQUES = []
for c in COMMUNES_AURA_5000:
    if c['url'] not in seen_urls:
        seen_urls.add(c['url'])
        COMMUNES_UNIQUES.append(c)

print_lock = Lock()
projets_lock = Lock()

class ScraperRapide:
    def __init__(self):
        self.session = requests.Session()
        self.projets: List[ProjetChaufferie] = []
        self.stats = {'scanned': 0, 'bulletins': 0, 'projets': 0, 'errors': 0}
    
    def fetch(self, url: str, timeout: int = 10) -> Optional[BeautifulSoup]:
        try:
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'fr-FR,fr;q=0.9',
            }
            r = self.session.get(url, headers=headers, timeout=timeout, verify=False)
            if r.status_code == 200:
                return BeautifulSoup(r.content, 'html.parser')
        except:
            pass
        return None
    
    def find_bulletin_pages(self, base_url: str) -> List[str]:
        urls = []
        patterns = ['/bulletin', '/bulletins', '/publications', '/magazine', '/journal', '/actualites']
        
        soup = self.fetch(base_url)
        if soup:
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').lower()
                text = link.get_text().lower()
                if any(p in href or p.replace('/', '') in text for p in patterns):
                    full = urljoin(base_url, link['href'])
                    if full not in urls:
                        urls.append(full)
        
        for pattern in patterns[:3]:
            url = urljoin(base_url, pattern)
            if url not in urls:
                urls.append(url)
        
        return urls[:3]
    
    def analyze_page(self, url: str, commune: str, dept: str, pop: int) -> Optional[ProjetChaufferie]:
        soup = self.fetch(url)
        if not soup:
            return None
        
        text = soup.get_text(separator=' ', strip=True).lower()
        
        # Chercher mots-clés chaufferie
        mots = [m for m in MOTS_CLES if m.lower() in text]
        if not mots:
            return None
        
        # Chercher contexte
        ctx = [c for c in CONTEXTE if c.lower() in text]
        
        # Extraire passage
        extrait = ""
        for mot in mots:
            pos = text.find(mot.lower())
            if pos != -1:
                extrait = text[max(0, pos-150):pos+250]
                break
        
        # Contact
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', soup.get_text())
        tels = re.findall(r'0[1-9][\s\.\-]?(?:[0-9]{2}[\s\.\-]?){4}', soup.get_text())
        contact = ', '.join(list(set(emails[:2] + tels[:2])))
        
        return ProjetChaufferie(
            commune=commune,
            departement=dept,
            source_type='bulletin' if 'bulletin' in url.lower() else 'municipal',
            titre=soup.title.string[:100] if soup.title else 'Sans titre',
            extrait=extrait[:400],
            mots_cles=mots + ctx,
            phase='reflexion' if any(p in text for p in ['réflexion', 'projet', 'étude']) else 'détecté',
            url=url,
            contact=contact if contact else None,
            population=pop
        )
    
    def scan_commune(self, info: Dict):
        commune = info['commune']
        dept = info['dept']
        base = info['url']
        pop = info.get('pop', 0)
        
        with print_lock:
            print(f"  🔍 {commune} ({dept})")
        
        self.stats['scanned'] += 1
        
        # Chercher bulletins
        bulletin_urls = self.find_bulletin_pages(base)
        if bulletin_urls:
            with print_lock:
                print(f"    📰 {len(bulletin_urls)} pages")
            self.stats['bulletins'] += len(bulletin_urls)
        
        # Analyser
        urls_to_check = bulletin_urls + [base]
        for url in urls_to_check[:5]:
            projet = self.analyze_page(url, commune, dept, pop)
            if projet:
                with projets_lock:
                    self.projets.append(projet)
                    self.stats['projets'] += 1
                with print_lock:
                    print(f"    🎯 PROJET: {projet.mots_cles[:3]}")
            time.sleep(random.uniform(0.3, 0.8))
        
        time.sleep(random.uniform(0.5, 1))
    
    def run(self):
        print("🚀 SCRAPER AURA - COMMUNES 5000+ HABITANTS")
        print(f"📊 {len(COMMUNES_UNIQUES)} communes à scanner")
        print("=" * 60)
        
        for info in COMMUNES_UNIQUES:
            try:
                self.scan_commune(info)
            except Exception as e:
                self.stats['errors'] += 1
        
        self.report()
    
    def report(self):
        print("\n" + "=" * 60)
        print("📊 RAPPORT FINAL")
        print("=" * 60)
        print(f"  • Communes scannées: {self.stats['scanned']}")
        print(f"  • Pages bulletins: {self.stats['bulletins']}")
        print(f"  • 🎯 PROJETS DÉTECTÉS: {self.stats['projets']}")
        print(f"  • Erreurs: {self.stats['errors']}")
        
        if self.projets:
            print(f"\n🔥 OPPORTUNITÉS CHAUFFERIE ({len(self.projets)}):")
            print("-" * 40)
            
            # Trier par population (plus gros budgets en premier)
            sorted_projets = sorted(self.projets, key=lambda x: x.population or 0, reverse=True)
            
            for i, p in enumerate(sorted_projets[:30], 1):  # Top 30
                print(f"\n{i}. 📍 {p.commune} ({p.departement}) - {p.population:,} hab")
                print(f"   🔑 {', '.join(p.mots_cles[:5])}")
                print(f"   📝 {p.extrait[:120]}...")
                if p.contact:
                    print(f"   📞 {p.contact}")
                print(f"   🔗 {p.url}")
            
            # Sauvegarder
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            fn = f'projets_aura_5000_{ts}.json'
            with open(fn, 'w', encoding='utf-8') as f:
                json.dump([asdict(p) for p in self.projets], f, ensure_ascii=False, indent=2)
            print(f"\n💾 Sauvegardé: {fn}")
        else:
            print("\n⚠️ Aucun projet trouvé")

import urllib3
urllib3.disable_warnings()

if __name__ == "__main__":
    ScraperRapide().run()
