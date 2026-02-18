"""
Module centralisé de chargement de la configuration de campagne de recherche.
Charge search_config.json et expose des accesseurs typés.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Chemin absolu vers le fichier de config (relatif à ce module)
_CONFIG_DIR = Path(__file__).parent
_CONFIG_PATH = _CONFIG_DIR / "search_config.json"

# Champs obligatoires de premier niveau
_REQUIRED_FIELDS = [
    "nom_campagne",
    "mots_cles",
    "prompt_ia",
    "zones_geographiques",
    "parametres_scraping",
    "seuil_ia",
]

# Sous-champs obligatoires de mots_cles
_REQUIRED_MOTS_CLES = ["prioritaires", "secondaires", "budget"]

_DEFAULT_CONFIG: Dict[str, Any] = {
    "nom_campagne": "Chaufferies Biomasse AURA",
    "description": "Détection projets chaufferie en phase amont",
    "mots_cles": {
        "prioritaires": [
            "chaufferie",
            "biomasse",
            "chaudière bois",
            "bois énergie",
            "réseau chaleur",
            "chaleur renouvelable",
        ],
        "secondaires": [
            "chauffage bois",
            "granulés",
            "plaquettes",
            "chaudière collective",
            "chaufferie collective",
            "modernisation chauffage",
        ],
        "budget": [
            "budget",
            "crédit",
            "investissement",
            "subvention",
            "fonds chaleur",
            "ademe",
            "cee",
        ],
    },
    "phases_projet": ["réflexion", "étude", "programmation", "consultation"],
    "prompt_ia": (
        "Tu es un expert en analyse de documents administratifs français, spécialisé "
        "dans la détection EXCLUSIVE de projets énergétiques collectifs (chaufferie "
        "biomasse, réseaux de chaleur, bois énergie).\n\n"
        "Ta mission : analyser le texte fourni et détecter UNIQUEMENT les documents "
        "réellement pertinents.\n\n"
        "DEFINITION DE PERTINENCE (tous les critères doivent être remplis) :\n"
        "1. Le document décrit UN PROJET CONCRET (étude, marché, délibération, "
        "convention, installation)\n"
        "2. Le projet concerne explicitement les mots-clés de la campagne en cours\n"
        "3. Le document contient PLUS que juste un accusé de réception ou en-tête "
        "administratif\n\n"
        "Réponds UNIQUEMENT au format JSON :\n"
        "{\n"
        '    "pertinent": true/false,\n'
        '    "score": 0-10,\n'
        '    "resume": "Résumé en 1 phrase",\n'
        '    "justification": "Pourquoi pertinent/non (20 mots max)"\n'
        "}"
    ),
    "zones_geographiques": {
        "departements": [
            "63", "03", "15", "43", "42", "69",
            "01", "07", "26", "38", "73", "74",
        ],
        "population_min": 500,
        "population_max": 50000,
    },
    "parametres_scraping": {
        "delai_entre_requetes": 1.5,
        "timeout": 30,
        "profondeur": "moyen",
        "seuil_confiance_min": 2,
    },
    "seuil_ia": 7,
    "date_debut_recherche": "2024-01-01",
    "version": "1.0.0",
    "derniere_modification": datetime.now().strftime("%Y-%m-%d"),
}


# ─────────────────────────────────────────────
# Validation interne
# ─────────────────────────────────────────────

def _validate(config: Dict[str, Any]) -> None:
    """Lève ValueError si un champ obligatoire est absent."""
    for field in _REQUIRED_FIELDS:
        if field not in config:
            raise ValueError(f"Champ obligatoire manquant dans search_config.json : '{field}'")

    mots_cles = config.get("mots_cles", {})
    for sub in _REQUIRED_MOTS_CLES:
        if sub not in mots_cles:
            raise ValueError(
                f"Sous-champ obligatoire manquant dans mots_cles : '{sub}'"
            )


# ─────────────────────────────────────────────
# API publique
# ─────────────────────────────────────────────

def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Charge et valide search_config.json.

    Args:
        config_path: Chemin alternatif vers le fichier JSON.
                     Si None, utilise config/search_config.json.

    Returns:
        Dictionnaire de configuration complet.

    Raises:
        FileNotFoundError: Fichier introuvable.
        json.JSONDecodeError: JSON invalide.
        ValueError: Champ obligatoire manquant.
    """
    path = Path(config_path) if config_path else _CONFIG_PATH

    if not path.exists():
        raise FileNotFoundError(
            f"Fichier de configuration introuvable : {path}\n"
            "Appelez reset_config() pour recréer le fichier par défaut."
        )

    with open(path, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    _validate(config)
    return config


def get_mots_cles(config_path: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Retourne les mots-clés de la campagne.

    Returns:
        Dict avec les clés 'prioritaires', 'secondaires', 'budget'.
    """
    return load_config(config_path)["mots_cles"]


def get_prompt_ia(config_path: Optional[str] = None) -> str:
    """
    Retourne le prompt système pour Ollama/Mistral.
    Le prompt est enrichi dynamiquement avec les mots-clés prioritaires.
    """
    config = load_config(config_path)
    prompt = config["prompt_ia"]

    # Injection dynamique des mots-clés prioritaires dans le prompt
    mots_prioritaires = config["mots_cles"].get("prioritaires", [])
    if mots_prioritaires:
        liste = ", ".join(mots_prioritaires)
        prompt = prompt.replace(
            "les mots-clés de la campagne en cours",
            f"les mots-clés suivants : {liste}",
        )

    return prompt


def get_zones(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Retourne la configuration des zones géographiques.

    Returns:
        Dict avec 'departements', 'population_min', 'population_max'.
    """
    return load_config(config_path)["zones_geographiques"]


def get_parametres(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Retourne les paramètres de scraping.

    Returns:
        Dict avec 'delai_entre_requetes', 'timeout', 'profondeur',
        'seuil_confiance_min'.
    """
    return load_config(config_path)["parametres_scraping"]


def get_seuil_ia(config_path: Optional[str] = None) -> int:
    """Retourne le seuil de score IA minimum (défaut : 7)."""
    return int(load_config(config_path).get("seuil_ia", 7))


def save_config(config: Dict[str, Any], config_path: Optional[str] = None) -> bool:
    """
    Valide et sauvegarde la configuration dans search_config.json.

    Args:
        config: Dictionnaire de configuration à sauvegarder.
        config_path: Chemin alternatif. Si None, écrase search_config.json.

    Returns:
        True si succès, False sinon.
    """
    path = Path(config_path) if config_path else _CONFIG_PATH

    try:
        _validate(config)
        config["derniere_modification"] = datetime.now().strftime("%Y-%m-%d")
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(config, fh, ensure_ascii=False, indent=2)

        return True

    except (ValueError, OSError) as exc:
        print(f"[config_loader] Erreur sauvegarde : {exc}")
        return False


def reset_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Réinitialise search_config.json avec les valeurs par défaut biomasse.

    Returns:
        La configuration par défaut.
    """
    config = json.loads(json.dumps(_DEFAULT_CONFIG))  # deep copy
    config["derniere_modification"] = datetime.now().strftime("%Y-%m-%d")
    save_config(config, config_path)
    return config


# ─────────────────────────────────────────────
# Presets prédéfinis
# ─────────────────────────────────────────────

PRESETS: Dict[str, Dict[str, Any]] = {
    "chaufferies_biomasse": {
        "nom_campagne": "Chaufferies Biomasse AURA",
        "description": "Détection projets chaufferie en phase amont",
        "mots_cles": {
            "prioritaires": ["chaufferie", "biomasse", "chaudière bois", "bois énergie", "réseau chaleur", "chaleur renouvelable"],
            "secondaires": ["chauffage bois", "granulés", "plaquettes", "chaudière collective", "chaufferie collective", "modernisation chauffage"],
            "budget": ["budget", "crédit", "investissement", "subvention", "fonds chaleur", "ademe", "cee"],
        },
        "seuil_ia": 7,
    },
    "panneaux_solaires": {
        "nom_campagne": "Panneaux Solaires / Photovoltaïque",
        "description": "Détection projets solaires PV sur bâtiments publics",
        "mots_cles": {
            "prioritaires": ["photovoltaïque", "panneaux solaires", "centrale solaire", "toiture solaire", "autoconsommation"],
            "secondaires": ["énergie solaire", "PV", "ombrière", "carport solaire", "installation solaire", "raccordement réseau"],
            "budget": ["budget", "investissement", "subvention", "prime autoconsommation", "CEE", "ADEME"],
        },
        "seuil_ia": 7,
    },
    "pompes_chaleur": {
        "nom_campagne": "Pompes à Chaleur",
        "description": "Détection projets PAC pour bâtiments publics",
        "mots_cles": {
            "prioritaires": ["pompe à chaleur", "PAC", "géothermie", "aérothermie", "thermodynamique"],
            "secondaires": ["chauffage renouvelable", "remplacement chaudière", "rénovation chauffage", "COP", "frigories"],
            "budget": ["budget", "investissement", "subvention", "MaPrimeRénov", "CEE", "ADEME"],
        },
        "seuil_ia": 7,
    },
    "bornes_recharge": {
        "nom_campagne": "Bornes de Recharge VE",
        "description": "Détection projets bornes électriques véhicules",
        "mots_cles": {
            "prioritaires": ["borne recharge", "véhicule électrique", "IRVE", "recharge électrique", "mobilité électrique"],
            "secondaires": ["parking électrique", "infrastructure recharge", "point de charge", "charge rapide", "charge lente"],
            "budget": ["budget", "investissement", "subvention", "ADVENIR", "DSIL", "DETR"],
        },
        "seuil_ia": 6,
    },
    "renovation_batiments": {
        "nom_campagne": "Rénovation Bâtiments Publics",
        "description": "Détection projets rénovation énergétique bâtiments communaux",
        "mots_cles": {
            "prioritaires": ["rénovation énergétique", "isolation thermique", "BBC", "performance énergétique", "DPE"],
            "secondaires": ["isolation façade", "isolation toiture", "menuiseries", "ventilation", "audit énergétique", "bilan thermique"],
            "budget": ["budget", "investissement", "subvention", "DETR", "DSIL", "certificats économies énergie"],
        },
        "seuil_ia": 6,
    },
    "voirie_reseaux": {
        "nom_campagne": "Voirie et Réseaux",
        "description": "Détection projets voirie, assainissement, eau potable",
        "mots_cles": {
            "prioritaires": ["voirie", "assainissement", "eau potable", "réseau eau", "chaussée"],
            "secondaires": ["trottoir", "canalisations", "station épuration", "STEP", "réseau pluvial", "éclairage public"],
            "budget": ["budget", "investissement", "subvention", "DETR", "DSIL", "fonds européens"],
        },
        "seuil_ia": 6,
    },
}


def get_presets() -> Dict[str, Dict[str, Any]]:
    """Retourne tous les presets disponibles."""
    return PRESETS


if __name__ == "__main__":
    # Auto-test rapide
    try:
        cfg = load_config()
        print(f"[OK] Campagne : {cfg['nom_campagne']}")
        print(f"[OK] Mots-clés prioritaires : {get_mots_cles()['prioritaires']}")
        print(f"[OK] Seuil IA : {get_seuil_ia()}")
        print(f"[OK] Prompt (50 premiers chars) : {get_prompt_ia()[:50]}...")
    except FileNotFoundError:
        print("[INFO] Fichier absent, création par défaut...")
        reset_config()
        print("[OK] search_config.json créé.")
