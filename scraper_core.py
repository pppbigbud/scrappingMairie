"""
ScraperCore — Scraper unifié sans mots-clés en dur.
Tous les paramètres viennent de config/config_loader.py.
"""

import os
import sys
import re
import json
import time
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ── Config loader ──────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config.config_loader import (
    get_mots_cles,
    get_parametres,
    get_zones,
    get_seuil_ia,
    load_config,
)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scraper_core")

# ── User-Agents ────────────────────────────────────────────────────────────────
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class ScraperCore:
    """
    Scraper générique piloté par search_config.json.
    Aucun mot-clé n'est codé en dur dans cette classe.
    """

    # Extensions de documents supportées
    DOC_EXTENSIONS = [".pdf", ".doc", ".docx"]

    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: Chemin alternatif vers search_config.json.
                         Si None, utilise config/search_config.json.
        """
        self._config_path = config_path
        self._reload_config()

    # ── Chargement / rechargement de la config ─────────────────────────────────

    def _reload_config(self) -> None:
        """Recharge la configuration depuis le fichier JSON."""
        self.mots_cles = get_mots_cles(self._config_path)
        self.parametres = get_parametres(self._config_path)
        self.zones = get_zones(self._config_path)
        self.seuil_confiance = int(self.parametres.get("seuil_confiance_min", 2))
        self.seuil_ia = get_seuil_ia(self._config_path)
        self.delai = float(self.parametres.get("delai_entre_requetes", 1.5))
        self.timeout = int(self.parametres.get("timeout", 30))
        log.info(
            "Config chargée — campagne : %s | mots prioritaires : %s",
            load_config(self._config_path).get("nom_campagne", "?"),
            self.mots_cles["prioritaires"][:3],
        )

    # ── Helpers HTTP ───────────────────────────────────────────────────────────

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _make_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(self._get_headers())
        return session

    # ── Analyse de texte ───────────────────────────────────────────────────────

    def analyser_texte(self, texte: str) -> Dict:
        """
        Analyse un texte et calcule un score de pertinence basé sur les
        mots-clés de la config (aucun mot-clé en dur).

        Returns:
            Dict avec 'score', 'pertinent', 'mots_trouves', 'details'.
        """
        texte_lower = texte.lower()
        details: Dict[str, List[str]] = {
            "prioritaires": [],
            "secondaires": [],
            "budget": [],
        }

        # Comptage pondéré : prioritaire = 2 pts, secondaire = 1 pt, budget = 1 pt
        for mot in self.mots_cles.get("prioritaires", []):
            if mot.lower() in texte_lower:
                details["prioritaires"].append(mot)

        for mot in self.mots_cles.get("secondaires", []):
            if mot.lower() in texte_lower:
                details["secondaires"].append(mot)

        for mot in self.mots_cles.get("budget", []):
            if mot.lower() in texte_lower:
                details["budget"].append(mot)

        score = (
            len(details["prioritaires"]) * 2
            + len(details["secondaires"])
            + len(details["budget"])
        )

        tous_mots = (
            details["prioritaires"] + details["secondaires"] + details["budget"]
        )

        return {
            "score": score,
            "pertinent": score >= self.seuil_confiance,
            "mots_trouves": tous_mots,
            "details": details,
        }

    # ── Filtrage des résultats ─────────────────────────────────────────────────

    def filtrer_resultats(self, resultats: List[Dict]) -> List[Dict]:
        """
        Filtre une liste de résultats selon le seuil de confiance de la config.

        Args:
            resultats: Liste de dicts avec au minimum la clé 'score'.

        Returns:
            Liste filtrée et triée par score décroissant.
        """
        filtres = [r for r in resultats if r.get("score", 0) >= self.seuil_confiance]
        return sorted(filtres, key=lambda r: r.get("score", 0), reverse=True)

    # ── Scraping d'un site ─────────────────────────────────────────────────────

    def scraper_site(
        self,
        url: str,
        commune: str,
        dept: Optional[str] = None,
        status_callback=None,
    ) -> List[Dict]:
        """
        Scrape un site municipal et retourne les documents pertinents.

        Args:
            url: URL de base du site municipal.
            commune: Nom de la commune.
            dept: Code département (ex: "63").
            status_callback: Callable(str) pour les messages de progression.

        Returns:
            Liste de dicts représentant les documents trouvés et analysés.
        """
        self._reload_config()  # Recharge à chaque appel pour refléter les changements

        def _log(msg: str, level: str = "info") -> None:
            getattr(log, level)(msg)
            if status_callback:
                status_callback(msg)

        _log(f"Scraping {commune} ({url})")
        session = self._make_session()
        found: List[Dict] = []

        try:
            time.sleep(random.uniform(self.delai * 0.5, self.delai * 1.5))
            response = session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            _log(f"Erreur connexion {url} : {exc}", "warning")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        all_links = soup.find_all("a", href=True)
        _log(f"{len(all_links)} liens trouvés sur la page principale")

        # Sections prioritaires à explorer
        sections = self._get_sections_prioritaires(url, soup)
        for section_url in sections:
            try:
                time.sleep(random.uniform(0.5, 1.5))
                r = session.get(section_url, timeout=self.timeout)
                if r.status_code == 200:
                    sub_soup = BeautifulSoup(r.text, "html.parser")
                    all_links.extend(sub_soup.find_all("a", href=True))
                    _log(f"Section explorée : {section_url}")
            except requests.RequestException:
                pass

        # Traitement des liens
        seen_urls = set()
        for link in all_links:
            href = link.get("href", "")
            if not href:
                continue

            full_url = urljoin(url, href)

            # Éviter les doublons et liens externes
            if full_url in seen_urls:
                continue
            if urlparse(full_url).netloc != urlparse(url).netloc:
                continue
            seen_urls.add(full_url)

            # Documents (PDF, DOC…)
            if self._is_document(full_url):
                filename = os.path.basename(urlparse(full_url).path) or full_url
                texte = self._extraire_texte_document(full_url, session, _log)
                if texte:
                    analyse = self.analyser_texte(texte)
                    doc = self._build_result(
                        filename, full_url, url, commune, dept, texte, analyse
                    )
                    found.append(doc)
                    _log(
                        f"Document : {filename[:50]} | score={analyse['score']} "
                        f"| pertinent={analyse['pertinent']}"
                    )

            # Pages HTML pertinentes
            elif self._is_relevant_html(full_url):
                try:
                    time.sleep(random.uniform(0.5, 1.0))
                    hr = session.get(full_url, timeout=self.timeout)
                    if hr.status_code == 200:
                        texte = self._extraire_texte_html(hr.text)
                        if texte and len(texte) > 300:
                            analyse = self.analyser_texte(texte)
                            filename = (
                                os.path.basename(urlparse(full_url).path) or "page.html"
                            )
                            doc = self._build_result(
                                filename, full_url, url, commune, dept, texte, analyse
                            )
                            doc["document_type"] = "html"
                            found.append(doc)
                except requests.RequestException:
                    pass

        pertinents = self.filtrer_resultats(found)
        _log(
            f"Terminé {commune} : {len(found)} docs trouvés, "
            f"{len(pertinents)} pertinents (seuil={self.seuil_confiance})"
        )
        return found

    # ── Helpers privés ─────────────────────────────────────────────────────────

    def _get_sections_prioritaires(self, base_url: str, soup: BeautifulSoup) -> List[str]:
        """Retourne les URLs des sections à explorer en priorité."""
        keywords = [
            "deliberation", "conseil", "bulletin", "document", "publication",
            "energie", "transition", "projet", "marche", "budget",
        ]
        sections = []
        for link in soup.find_all("a", href=True):
            href = link.get("href", "").lower()
            if any(kw in href for kw in keywords):
                full = urljoin(base_url, link["href"])
                if urlparse(full).netloc == urlparse(base_url).netloc:
                    sections.append(full)
        return list(dict.fromkeys(sections))[:15]  # dédoublonnage, max 15

    def _is_document(self, url: str) -> bool:
        url_lower = url.lower()
        return any(url_lower.endswith(ext) or ext in url_lower for ext in self.DOC_EXTENSIONS)

    def _is_relevant_html(self, url: str) -> bool:
        url_lower = url.lower()
        html_keywords = [
            "deliberation", "conseil", "bulletin", "energie",
            "transition", "projet", "budget",
        ]
        return any(kw in url_lower for kw in html_keywords)

    def _extraire_texte_document(
        self, url: str, session: requests.Session, log_fn
    ) -> Optional[str]:
        """Télécharge et extrait le texte d'un document (PDF/DOC)."""
        try:
            time.sleep(random.uniform(self.delai * 0.5, self.delai))
            r = session.get(url, timeout=self.timeout)
            r.raise_for_status()

            if url.lower().endswith(".pdf") or "pdf" in url.lower():
                try:
                    import pdfplumber
                    import io
                    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                        textes = [p.extract_text() or "" for p in pdf.pages[:10]]
                    return "\n".join(textes).strip() or None
                except Exception as exc:
                    log_fn(f"pdfplumber échoué pour {url} : {exc}", "warning")
                    return None
            else:
                # Pour HTML ou autres, retourne le texte brut
                soup = BeautifulSoup(r.text, "html.parser")
                return self._extraire_texte_html(r.text)

        except requests.RequestException as exc:
            log_fn(f"Erreur téléchargement {url} : {exc}", "warning")
            return None

    def _extraire_texte_html(self, html: str) -> str:
        """Extrait le texte utile d'une page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        lines = [l.strip() for l in soup.get_text(separator="\n").split("\n") if l.strip()]
        return "\n".join(lines)

    def _build_result(
        self,
        filename: str,
        source_url: str,
        site_url: str,
        commune: str,
        dept: Optional[str],
        texte: str,
        analyse: Dict,
    ) -> Dict:
        return {
            "nom_fichier": filename,
            "source_url": source_url,
            "site_url": site_url,
            "commune": commune,
            "departement": dept,
            "date_detection": datetime.now().isoformat(),
            "texte": texte[:50000],
            "score": analyse["score"],
            "pertinent": analyse["pertinent"],
            "mots_trouves": analyse["mots_trouves"],
            "details_mots": analyse["details"],
            "ia_pertinent": False,
            "ia_score": 0,
            "ia_resume": "",
            "ia_justification": "",
            "document_type": "pdf",
            "statut": "completed",
        }

    # ── Sauvegarde ─────────────────────────────────────────────────────────────

    def sauvegarder_resultats(
        self, resultats: List[Dict], output_dir: str = "data"
    ) -> str:
        """Sauvegarde les résultats dans data/<timestamp>.json."""
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(output_dir, f"resultats_{ts}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(resultats, fh, ensure_ascii=False, indent=2)
        log.info("Résultats sauvegardés : %s (%d docs)", path, len(resultats))
        return path


# ── Point d'entrée rapide ──────────────────────────────────────────────────────

if __name__ == "__main__":
    scraper = ScraperCore()
    print(f"Mots-clés prioritaires : {scraper.mots_cles['prioritaires']}")
    print(f"Seuil confiance : {scraper.seuil_confiance}")
    print(f"Seuil IA : {scraper.seuil_ia}")

    # Test analyser_texte
    texte_test = (
        "La commune envisage l'installation d'une chaufferie biomasse "
        "avec un réseau chaleur de 2 km. Budget prévisionnel : 1,2 M€. "
        "Subvention ADEME sollicitée."
    )
    resultat = scraper.analyser_texte(texte_test)
    print(f"Test analyse : score={resultat['score']} | pertinent={resultat['pertinent']}")
    print(f"Mots trouvés : {resultat['mots_trouves']}")
