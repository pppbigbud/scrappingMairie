#!/usr/bin/env python3
import json
import os
from datetime import datetime

# Créer quelques fichiers JSON de test pour démonstration
PDF_DATA_DIR = '../openclaw_backup_20260201_1306/data/pdf_texts/www.mairie-trevoux.fr_'

# Documents de test avec différents scores et pertinences
test_documents = [
    {
        "nom_fichier": "test-projet-solaire.pdf",
        "source_url": "https://www.mairie-trevoux.fr/documents/solaire",
        "site_url": "https://www.mairie-trevoux.fr/",
        "date_detection": datetime.now().isoformat(),
        "statut": "completed",
        "texte": "Ce document présente un projet d'installation de panneaux solaires sur les toits de la mairie. Le projet inclut l'installation de 100m² de panneaux photovoltaïques pour une production estimée à 15000 kWh par an. Cette installation permettra de réduire la consommation énergétique de 30% et de générer des revenus par la revente d'électricité.",
        "erreur": None,
        "ia_pertinent": True,
        "ia_score": 9,
        "ia_resume": "Projet d'installation de panneaux solaires photovoltaïques sur les toits de la mairie avec production de 15000 kWh/an.",
        "ia_justification": "Document pertinent car il décrit un projet concret d'énergie solaire avec chiffres détaillés et objectifs de réduction de consommation.",
        "ia_timestamp": datetime.now().isoformat()
    },
    {
        "nom_fichier": "test-chaufferie-biomasse.pdf",
        "source_url": "https://www.mairie-trevoux.fr/documents/biomasse",
        "site_url": "https://www.mairie-trevoux.fr/",
        "date_detection": datetime.now().isoformat(),
        "statut": "completed",
        "texte": "Étude de faisabilité pour une chaufferie biomasse communale. Le projet prévoit le remplacement de l'ancienne chaufferie au fioul par une installation moderne fonctionnant au bois énergie local. La puissance estimée est de 500kW et desservira les bâtiments publics principaux. Le retour sur investissement est prévu sur 8 ans.",
        "erreur": None,
        "ia_pertinent": True,
        "ia_score": 8,
        "ia_resume": "Étude de faisabilité pour une chaufferie biomasse de 500kW remplaçant l'installation au fioul existante.",
        "ia_justification": "Très pertinent : projet de transition énergétique concret avec biomasse locale et chiffres économiques détaillés.",
        "ia_timestamp": datetime.now().isoformat()
    },
    {
        "nom_fichier": "test-isolation-batiments.pdf",
        "source_url": "https://www.mairie-trevoux.fr/documents/isolation",
        "site_url": "https://www.mairie-trevoux.fr/",
        "date_detection": datetime.now().isoformat(),
        "statut": "completed",
        "texte": "Programme de rénovation énergétique des bâtiments communaux. Les travaux incluent l'isolation des combles, le remplacement des fenêtres par du double vitrage et l'amélioration de l'isolation des murs. Budget prévisionnel de 200000 euros avec subventions attendues de l'ADEME.",
        "erreur": None,
        "ia_pertinent": True,
        "ia_score": 7,
        "ia_resume": "Programme de rénovation énergétique des bâtiments communaux avec isolation et double vitrage.",
        "ia_justification": "Pertinent car il s'agit de rénovation énergétique avec actions concrètes et budget défini.",
        "ia_timestamp": datetime.now().isoformat()
    },
    {
        "nom_fichier": "test-conseil-municipal.pdf",
        "source_url": "https://www.mairie-trevoux.fr/documents/conseil",
        "site_url": "https://www.mairie-trevoux.fr/",
        "date_detection": datetime.now().isoformat(),
        "statut": "completed",
        "texte": "Compte-rendu du conseil municipal du 15 septembre 2024. Points à l'ordre du jour : approbation des comptes, discussion sur le projet de parking, validation du budget pour les fêtes de fin d'année. Aucun sujet relatif à l'énergie ou aux projets environnementaux n'a été abordé lors de cette session.",
        "erreur": None,
        "ia_pertinent": False,
        "ia_score": 2,
        "ia_resume": "Compte-rendu du conseil municipal avec sujets administratifs courants.",
        "ia_justification": "Non pertinent : document administratif standard sans rapport avec les projets énergétiques.",
        "ia_timestamp": datetime.now().isoformat()
    },
    {
        "nom_fichier": "test-budget-annuel.pdf",
        "source_url": "https://www.mairie-trevoux.fr/documents/budget",
        "site_url": "https://www.mairie-trevoux.fr/",
        "date_detection": datetime.now().isoformat(),
        "statut": "completed",
        "texte": "Budget annuel de la commune pour l'exercice 2024. Présentation détaillée des recettes et dépenses prévisionnelles. Le poste énergie représente 15% du budget total. Une ligne budgétaire de 50000 euros est prévue pour les études énergétiques mais aucun projet spécifique n'est détaillé.",
        "erreur": None,
        "ia_pertinent": False,
        "ia_score": 3,
        "ia_resume": "Budget annuel communal avec une ligne pour les études énergétiques mais sans projet concret.",
        "ia_justification": "Peu pertinent : mention budgétaire énergie mais pas de projet d'énergie renouvelable ou d'infrastructure spécifique.",
        "ia_timestamp": datetime.now().isoformat()
    }
]

# Créer les fichiers JSON
for i, doc in enumerate(test_documents, 1):
    filename = f"test-document-{i:02d}.json"
    filepath = os.path.join(PDF_DATA_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    
    print(f"Créé: {filename}")

print(f"\n✅ {len(test_documents)} documents de test créés dans {PDF_DATA_DIR}")
