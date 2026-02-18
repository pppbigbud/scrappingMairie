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
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import hashlib
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
import trafilatura
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import feedparser as _feedparser
    _HAS_FEEDPARSER = True
except ImportError:
    _HAS_FEEDPARSER = False

try:
    from dateutil import parser as _dateutil_parser
    _HAS_DATEUTIL = True
except ImportError:
    _HAS_DATEUTIL = False

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


# ── Signaux faibles ────────────────────────────────────────────────────────────
SIGNAUX_FAIBLES = {
    "budgetaires": [
        "budget primitif", "plan pluriannuel d'investissement", "ppi",
        "programmation budgétaire", "autorisation de programme",
        "crédit de paiement", "ligne budgétaire énergie",
        "section d'investissement", "dotation", "enveloppe budgétaire",
    ],
    "reflexion": [
        "étude de faisabilité", "diagnostic énergétique", "audit énergétique",
        "bilan carbone", "transition énergétique", "plan climat", "pcaet",
        "rénovation thermique", "sobriété énergétique", "décarbonation",
        "bilan thermique", "dpe", "performance énergétique",
    ],
    "consultation": [
        "appel à manifestation d'intérêt", "ami énergie", "concertation",
        "marché de maîtrise d'œuvre", "mission d'étude", "prestataire énergie",
        "appel d'offres", "dce", "cahier des charges", "consultation entreprise",
        "marché public travaux",
    ],
}

# Niveau de maturité : (label, emoji, bonus_score, délai_estimé)
MATURITE_NIVEAUX = {
    "consultation": ("Consultation imminente", "🔴", 4, "< 3 mois"),
    "programmation": ("Programmation",         "🟠", 3, "3-6 mois"),
    "etude":         ("Étude",                 "🟡", 2, "6-12 mois"),
    "reflexion":     ("Réflexion",             "🟢", 1, "12+ mois"),
}

# Sources prioritaires (ordre de priorité décroissant)
SOURCE_PRIORITES = {
    "rss":          ("Flux RSS",        2),
    "deliberation": ("Délibération",    2),
    "actualites":   ("Actualités",      1),
    "bulletin":     ("Bulletin",        1),
    "accueil":      ("Accueil",         0),
    "generique":    ("Page générique",  0),
}

# Mots-clés URL pour trier les sections par potentiel (priorité décroissante)
_PRIORITE_MOTS: List[List[str]] = [
    ["deliber", "conseil", "budget", "marche", "projet", "energie", "travaux", "document", "rapport"],
    ["actu", "news", "article", "bulletin"],
]

# Patterns URL pour détecter les sections prioritaires
_SECTION_PATTERNS = {
    "actualites":   re.compile(r'actual|news|agenda|evenement', re.I),
    "deliberation": re.compile(r'deliber|conseil.munic|compte.rendu|seance|pv.conseil', re.I),
    "bulletin":     re.compile(r'bulletin|magazine|journal.munic|lettre.info', re.I),
    "budget":       re.compile(r'budget|finances|investissement', re.I),
}

# Patterns date textuels
_DATE_PATTERNS = [
    re.compile(r'(?:publié|mis à jour|modifié|date)\s*(?:le|:)?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})', re.I),
    re.compile(r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})', re.I),
    re.compile(r'(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})'),
]

_MOIS_FR = {
    'janvier':1,'février':2,'mars':3,'avril':4,'mai':5,'juin':6,
    'juillet':7,'août':8,'septembre':9,'octobre':10,'novembre':11,'décembre':12,
}


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
        cfg = load_config(self._config_path)
        # Fenêtre temporelle (jours) — défaut 90
        self.fenetre_jours = int(cfg.get("fenetre_temporelle", 90))
        # Signaux faibles actifs par catégorie
        sf_cfg = cfg.get("signaux_faibles_actifs", {"budgetaires": True, "reflexion": True, "consultation": True})
        self.signaux_actifs = sf_cfg
        # Maturité minimale à afficher
        self.maturite_min = cfg.get("maturite_min", "reflexion")
        log.info(
            "Config chargée — campagne : %s | fenêtre : %dj | mots prioritaires : %s",
            cfg.get("nom_campagne", "?"),
            self.fenetre_jours,
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
        session.verify = False
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        log.debug("⚠️ SSL non vérifié (mode permissif activé)")
        return session

    # ── Extraction de date ─────────────────────────────────────────────────────

    def extraire_date(self, soup: Optional[BeautifulSoup] = None,
                      texte: str = "", url: str = "") -> Optional[datetime]:
        """
        Tente d'extraire une date de publication depuis :
        1. Balises HTML <time>, <date>
        2. Métadonnées OpenGraph og:updated_time / og:published_time / article:published_time
        3. Patterns textuels "publié le", "mis à jour le"
        4. Nom de fichier PDF avec date (ex: CR_2024-03-15.pdf)
        5. dateutil en dernier recours
        Retourne un datetime UTC naïf ou None.
        """
        now = datetime.utcnow()

        # 1. Balises <time>
        if soup:
            for tag in soup.find_all(["time", "date"]):
                dt_attr = tag.get("datetime") or tag.get("content") or tag.get_text(strip=True)
                parsed = self._parse_date_str(dt_attr)
                if parsed:
                    return parsed

            # 2. OpenGraph / meta
            for prop in ("og:updated_time", "og:published_time", "article:published_time",
                         "article:modified_time", "DC.date"):
                meta = soup.find("meta", attrs={"property": prop}) or \
                       soup.find("meta", attrs={"name": prop})
                if meta:
                    parsed = self._parse_date_str(meta.get("content", ""))
                    if parsed:
                        return parsed

        # 3. Patterns textuels
        for pat in _DATE_PATTERNS:
            m = pat.search(texte)
            if m:
                parsed = self._parse_date_match(m)
                if parsed:
                    return parsed

        # 4. Nom de fichier PDF
        fname = os.path.basename(urlparse(url).path)
        m = re.search(r'(\d{4})[_\-](\d{2})[_\-](\d{2})', fname)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass

        return None

    def _parse_date_str(self, s: str) -> Optional[datetime]:
        """Parse une chaîne de date avec dateutil ou regex."""
        if not s or len(s) < 6:
            return None
        s = s.strip()
        if _HAS_DATEUTIL:
            try:
                dt = _dateutil_parser.parse(s, dayfirst=True)
                return dt.replace(tzinfo=None)
            except Exception:
                pass
        # Fallback ISO
        m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass
        return None

    def _parse_date_match(self, m: re.Match) -> Optional[datetime]:
        """Convertit un match regex de date en datetime."""
        groups = m.groups()
        try:
            if len(groups) == 3 and any(g in _MOIS_FR for g in groups):
                # Format "15 janvier 2024"
                jour, mois_str, annee = groups
                mois = _MOIS_FR.get(mois_str.lower(), 0)
                if mois:
                    return datetime(int(annee), mois, int(jour))
            elif len(groups) == 1:
                # Format "15/03/2024" ou "2024-03-15"
                return self._parse_date_str(groups[0])
            elif len(groups) == 3:
                # Format "2024/03/15"
                return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
        except (ValueError, TypeError):
            pass
        return None

    def est_dans_fenetre(self, date_pub: Optional[datetime]) -> bool:
        """Vérifie si une date est dans la fenêtre temporelle configurée."""
        if date_pub is None:
            return True  # Pas de date = on garde (bénéfice du doute)
        cutoff = datetime.utcnow() - timedelta(days=self.fenetre_jours)
        return date_pub >= cutoff

    # ── Détection RSS ──────────────────────────────────────────────────────────

    def detecter_flux_rss(self, base_url: str, soup: BeautifulSoup,
                          session: requests.Session) -> List[Dict]:
        """
        Détecte et parse les flux RSS du site.
        Retourne une liste de dicts {titre, url, date, texte, source_type}.
        """
        entries = []
        rss_urls = []

        # Détection via balise <link rel="alternate" type="application/rss+xml">
        for link in soup.find_all("link", rel="alternate"):
            t = link.get("type", "")
            if "rss" in t or "atom" in t or "xml" in t:
                href = link.get("href", "")
                if href:
                    rss_urls.append(urljoin(base_url, href))

        # Patterns URL courants si aucune balise trouvée
        if not rss_urls:
            for candidate in ["/feed", "/rss", "/feed.xml", "/rss.xml",
                               "/spip.php?page=backend", "/index.php?option=com_content&format=feed"]:
                rss_urls.append(urljoin(base_url, candidate))

        for rss_url in rss_urls[:3]:
            try:
                if _HAS_FEEDPARSER:
                    feed = _feedparser.parse(rss_url)
                    if not feed.entries:
                        continue
                    for entry in feed.entries[:20]:
                        pub_date = None
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            try:
                                pub_date = datetime(*entry.published_parsed[:6])
                            except Exception:
                                pass
                        texte = entry.get("summary", "") or entry.get("title", "")
                        entries.append({
                            "titre": entry.get("title", ""),
                            "url": entry.get("link", rss_url),
                            "date_publication": pub_date,
                            "texte": texte,
                            "source_type": "rss",
                        })
                else:
                    # Sans feedparser : GET brut + parse XML minimal
                    r = session.get(rss_url, timeout=self.timeout)
                    if r.status_code == 200 and ("<rss" in r.text or "<feed" in r.text):
                        rss_soup = BeautifulSoup(r.text, "xml")
                        for item in rss_soup.find_all(["item", "entry"])[:20]:
                            titre = (item.find("title") or item.find("name"))
                            lien  = (item.find("link") or item.find("url"))
                            desc  = item.find("description") or item.find("summary")
                            pub   = item.find("pubDate") or item.find("published") or item.find("updated")
                            pub_date = self._parse_date_str(pub.get_text() if pub else "")
                            entries.append({
                                "titre": titre.get_text(strip=True) if titre else "",
                                "url": lien.get_text(strip=True) if lien else rss_url,
                                "date_publication": pub_date,
                                "texte": desc.get_text(strip=True) if desc else "",
                                "source_type": "rss",
                            })
            except Exception:
                pass

        return entries

    # ── Signaux faibles & maturité ─────────────────────────────────────────────

    def analyser_signaux_faibles(self, texte: str) -> Dict:
        """
        Détecte les signaux faibles dans le texte selon les catégories actives.
        Retourne {signaux_trouves, categories, maturite, bonus_score}.
        """
        texte_lower = texte.lower()
        signaux_trouves: Dict[str, List[str]] = {}
        categories_trouvees = set()

        for cat, mots in SIGNAUX_FAIBLES.items():
            if not self.signaux_actifs.get(cat, True):
                continue
            trouves = [m for m in mots if m.lower() in texte_lower]
            if trouves:
                signaux_trouves[cat] = trouves
                categories_trouvees.add(cat)

        # Déterminer la maturité (priorité : consultation > budgetaires > reflexion)
        maturite = "reflexion"
        if "consultation" in categories_trouvees:
            maturite = "consultation"
        elif "budgetaires" in categories_trouvees:
            maturite = "programmation"
        elif "reflexion" in categories_trouvees:
            maturite = "etude"

        bonus = MATURITE_NIVEAUX[maturite][2]
        return {
            "signaux_trouves": signaux_trouves,
            "categories": list(categories_trouvees),
            "maturite": maturite,
            "maturite_label": MATURITE_NIVEAUX[maturite][0],
            "maturite_emoji": MATURITE_NIVEAUX[maturite][1],
            "maturite_delai": MATURITE_NIVEAUX[maturite][3],
            "bonus_signaux": len([m for lst in signaux_trouves.values() for m in lst]),
            "bonus_maturite": bonus,
        }

    # ── Scoring composite ──────────────────────────────────────────────────────

    def calculer_score_composite(self, analyse_kw: Dict, analyse_sf: Dict,
                                  date_pub: Optional[datetime],
                                  source_type: str) -> Dict:
        """
        Score composite :
        - Fraîcheur : -1 pt / semaine d'ancienneté (max 12 semaines)
        - Pertinence : +3 pts / mot-clé direct, +1 pt / signal faible
        - Source : +2 si RSS/délibération, +1 si bulletin, 0 sinon
        - Maturité : +4 consultation, +3 programmation, +2 étude, +1 réflexion
        """
        details = {}

        # Fraîcheur
        score_fraicheur = 0
        if date_pub:
            semaines = (datetime.utcnow() - date_pub).days / 7
            score_fraicheur = -min(int(semaines), 12)
        details["fraicheur"] = score_fraicheur

        # Pertinence mots-clés directs
        nb_directs = (len(analyse_kw.get("details", {}).get("prioritaires", [])) * 3
                      + len(analyse_kw.get("details", {}).get("secondaires", [])) * 1
                      + len(analyse_kw.get("details", {}).get("budget", [])) * 1)
        details["pertinence_kw"] = nb_directs

        # Signaux faibles
        nb_sf = analyse_sf.get("bonus_signaux", 0)
        details["signaux_faibles"] = nb_sf

        # Source
        src_bonus = SOURCE_PRIORITES.get(source_type, ("", 0))[1]
        details["source"] = src_bonus

        # Maturité
        mat_bonus = analyse_sf.get("bonus_maturite", 1)
        details["maturite"] = mat_bonus

        total = score_fraicheur + nb_directs + nb_sf + src_bonus + mat_bonus
        details["total"] = total

        return {"score_composite": total, "score_details": details}

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
        Scrape un site municipal avec priorisation des sources fraîches :
        1. Flux RSS  2. Actualités  3. Délibérations  4. Bulletins PDF  5. Accueil
        Filtre par fenêtre temporelle, détecte signaux faibles, calcule score composite.
        Logs diagnostics complets via status_callback.
        """
        self._reload_config()

        def _log(msg: str, level: str = "info") -> None:
            getattr(log, level)(msg)
            if status_callback:
                status_callback(msg, level)

        def _extrait_30_mots(texte: str) -> str:
            mots = texte.split()[:30]
            return " ".join(mots) + ("…" if len(texte.split()) > 30 else "")

        # ── Compteurs bilan ────────────────────────────────────────────────────
        bilan = {
            "pages_visitees": 0,
            "pdfs_tentes": 0,
            "pdfs_reussis": 0,
            "pdfs_scannes": 0,
            "docs_avec_mots_cles": 0,
            "docs_retenus": 0,
            "docs_ecartes": 0,
            "score_max": 0,
        }

        session = self._make_session()
        found: List[Dict] = []
        seen_urls: set = set()
        seen_hashes: set = set()
        base_netloc = urlparse(url).netloc

        # ── Étape 0 : Connexion page d'accueil ────────────────────────────────
        _log(f"🔍 [{commune}] Connexion → {url}")

        def _connecter(target_url: str) -> Optional[requests.Response]:
            """Tente une connexion et retourne la Response ou None."""
            t0 = time.time()
            try:
                r = session.get(target_url, timeout=self.timeout)
                elapsed_ms = int((time.time() - t0) * 1000)
                taille = len(r.content)
                has_body = "<body" in r.text.lower()
                _log(
                    f"   ↳ HTTP {r.status_code} | {taille:,} octets | {elapsed_ms} ms"
                    f" | body={'✅' if has_body else '❌'}"
                )
                if taille < 1000:
                    _log(
                        f"   ⚠️ Contenu suspect ({taille} octets) — possible blocage ou redirection",
                        "warning",
                    )
                if r.status_code == 403:
                    _log("   ❌ Accès refusé (403) — site bloqué", "warning")
                    return None
                r.raise_for_status()
                return r
            except requests.exceptions.SSLError as exc:
                _log(f"   🔒 Erreur SSL : {exc.__class__.__name__} — {str(exc)[:120]}", "warning")
                return None
            except requests.exceptions.Timeout:
                _log(f"   ⏱️ Timeout ({self.timeout}s dépassé)", "warning")
                return None
            except requests.exceptions.ConnectionError as exc:
                cause = str(exc)[:120]
                if "refused" in cause.lower():
                    _log(f"   🚫 Connexion refusée : {cause}", "warning")
                else:
                    _log(f"   🚫 Erreur de connexion : {cause}", "warning")
                return None
            except requests.exceptions.TooManyRedirects:
                _log("   🔄 Trop de redirections", "warning")
                return None
            except requests.RequestException as exc:
                _log(f"   ❓ Erreur inconnue : {exc.__class__.__name__} — {str(exc)[:120]}", "warning")
                return None

        time.sleep(random.uniform(self.delai * 0.5, self.delai * 1.5))
        response = _connecter(url)

        # Fallback HTTP si HTTPS a échoué
        if response is None and url.startswith("https://"):
            http_url = "http://" + url[len("https://"):]
            _log(f"   ⚠️ HTTPS échoué → tentative HTTP sur {http_url}", "warning")
            response = _connecter(http_url)
            if response is not None:
                url = http_url  # utiliser l'URL HTTP pour la suite
                base_netloc = urlparse(url).netloc

        if response is None:
            _log(f"   ❌ Impossible de joindre {commune} — site ignoré", "warning")
            return []

        bilan["pages_visitees"] += 1
        home_soup = BeautifulSoup(response.text, "html.parser")

        # ── Étape 1 : Flux RSS ────────────────────────────────────────────────
        rss_entries = self.detecter_flux_rss(url, home_soup, session)
        if rss_entries:
            _log(f"📡 RSS : {len(rss_entries)} entrée(s) détectée(s)")
        else:
            _log("   ℹ️ Aucun RSS détecté — passage aux sections HTML")

        rss_ecartees = 0
        rss_retenues = 0
        for entry in rss_entries:
            if not self.est_dans_fenetre(entry.get("date_publication")):
                rss_ecartees += 1
                continue
            texte = entry.get("texte", "") + " " + entry.get("titre", "")
            analyse = self.analyser_texte(texte)
            if not analyse["pertinent"]:
                rss_ecartees += 1
                continue
            sf = self.analyser_signaux_faibles(texte)
            sc = self.calculer_score_composite(analyse, sf, entry.get("date_publication"), "rss")
            doc = self._build_result(
                entry.get("titre", "rss_entry")[:80],
                entry.get("url", url), url, commune, dept, texte, analyse,
                source_type="rss",
                date_pub=entry.get("date_publication"),
                signaux_faibles=sf,
                score_composite=sc,
            )
            found.append(doc)
            seen_urls.add(entry.get("url", ""))
            rss_retenues += 1
            bilan["docs_retenus"] += 1
            bilan["score_max"] = max(bilan["score_max"], sc["score_composite"])

        if rss_entries:
            _log(
                f"   ↳ RSS : {rss_retenues} retenue(s), {rss_ecartees} écartée(s)"
                f" (hors fenêtre ou non pertinent)"
            )

        # ── Étape 2 : Sources prioritaires ────────────────────────────────────
        sources_prioritaires = self._get_sources_prioritaires(url, home_soup, base_netloc)
        if sources_prioritaires:
            _log(f"📂 {len(sources_prioritaires)} section(s) détectées")
            _log(f"📋 Ordre de visite : {[u for u, _ in sources_prioritaires[:10]]}" +
                 (f" … (+{len(sources_prioritaires)-10} autres)" if len(sources_prioritaires) > 10 else ""))
        else:
            _log("   ℹ️ Aucune section prioritaire détectée (délibérations, actualités…)")

        _TIMEOUT_MOTS = ["deliber", "conseil", "budget", "projet", "marche"]
        nb_sections = len(sources_prioritaires)
        for sec_idx, (section_url, section_type) in enumerate(sources_prioritaires, 1):
            if section_url in seen_urls:
                _log(f"   [{sec_idx}/{nb_sections}] ⏭️ Déjà visitée : {section_url}")
                continue
            sec_timeout = (
                self.timeout * 2
                if any(m in section_url.lower() for m in _TIMEOUT_MOTS)
                else self.timeout
            )
            try:
                time.sleep(random.uniform(0.5, 1.2))
                r = session.get(section_url, timeout=sec_timeout)
                bilan["pages_visitees"] += 1
                _log(
                    f"   [{sec_idx}/{nb_sections}] HTTP {r.status_code}"
                    f" | [{section_type}] {section_url}"
                )
                if r.status_code != 200:
                    _log(
                        f"   [{sec_idx}/{nb_sections}] ⚠️ Ignorée (HTTP {r.status_code})"
                        f" | {section_url}",
                        "warning",
                    )
                    continue

                texte_section = self._extraire_texte_html(r.text)
                nb_mots = len(texte_section.split())
                extrait = _extrait_30_mots(texte_section) if status_callback else ""

                if nb_mots < 100:
                    _log(
                        f"   [{sec_idx}/{nb_sections}] ⚠️ [{section_type}] {nb_mots} mots"
                        f" — vide ou non lisible | {section_url}",
                        "warning",
                    )
                else:
                    _log(
                        f"   [{sec_idx}/{nb_sections}] 📂 [{section_type}] {nb_mots} mots"
                        f" | {section_url}"
                    )
                    if status_callback and extrait:
                        _log(f'      Extrait : "{extrait}"')

                # Mots-clés dans la section + création doc HTML si pertinent
                analyse_section = self.analyser_texte(texte_section)
                if analyse_section["mots_trouves"]:
                    _log(f"      🔑 Mots-clés section : {analyse_section['mots_trouves']}")
                else:
                    _log("      — Aucun mot-clé trouvé dans cette section")

                # Bug 1 fix : créer un doc HTML si la section a un score > 0
                if analyse_section["score"] > 0:
                    page_soup_sec = BeautifulSoup(r.text, "html.parser")
                    date_pub_sec = self.extraire_date(
                        soup=page_soup_sec, texte=texte_section, url=section_url
                    )
                    if self.est_dans_fenetre(date_pub_sec):
                        sf_sec = self.analyser_signaux_faibles(texte_section)
                        sc_sec = self.calculer_score_composite(
                            analyse_section, sf_sec, date_pub_sec, section_type
                        )
                        fname_sec = (
                            os.path.basename(urlparse(section_url).path).strip("/")
                            or section_type
                        )
                        doc_sec = self._build_result(
                            fname_sec, section_url, url, commune, dept,
                            texte_section, analyse_section,
                            source_type=section_type,
                            date_pub=date_pub_sec,
                            signaux_faibles=sf_sec,
                            score_composite=sc_sec,
                        )
                        doc_sec["document_type"] = "html"
                        _hash = hashlib.md5(texte_section[:500].encode()).hexdigest()
                        if _hash in seen_hashes:
                            _log(f"      ⏭️ Contenu dupliqué ignoré : {fname_sec}")
                        else:
                            seen_hashes.add(_hash)
                            found.append(doc_sec)
                            bilan["docs_avec_mots_cles"] += 1
                            bilan["docs_retenus"] += 1
                            bilan["score_max"] = max(bilan["score_max"], sc_sec["score_composite"])
                            _log(
                                f"      ✅ Doc retenu : {fname_sec}"
                                f" | score={sc_sec['score_composite']}"
                                f" | {sf_sec['maturite_emoji']} {sf_sec['maturite_label']}"
                            )
                    else:
                        _log("      ⏭️ Section hors fenêtre temporelle — ignorée")

                sub_soup = BeautifulSoup(r.text, "html.parser")

                for link in sub_soup.find_all("a", href=True):
                    href = link.get("href", "")
                    # Résoudre l'URL relative par rapport à la section (pas la page d'accueil)
                    full_url = urljoin(section_url, href)
                    if full_url in seen_urls:
                        continue
                    if urlparse(full_url).netloc != base_netloc:
                        continue

                    if not self._is_document(full_url):
                        continue

                    # ── PDF / Document — marquer seulement les docs, pas les pages HTML ──
                    seen_urls.add(full_url)
                    fname = os.path.basename(urlparse(full_url).path) or full_url
                    _log(f"      📎 PDF détecté : {fname[:60]}")
                    bilan["pdfs_tentes"] += 1

                    date_fname = self.extraire_date(url=full_url)
                    if not self.est_dans_fenetre(date_fname):
                        _log(f"         ↳ ⏭️ Hors fenêtre temporelle (date fichier) — ignoré")
                        continue

                    texte, nb_pages, nb_chars = self._extraire_texte_document_verbose(
                        full_url, session, _log
                    )
                    if not texte:
                        bilan["pdfs_scannes"] += 1
                        continue

                    bilan["pdfs_reussis"] += 1

                    if nb_chars < 100:
                        _log(
                            f"         ⚠️ PDF probablement scanné (image) — {nb_chars} car. extraits",
                            "warning",
                        )
                        bilan["pdfs_scannes"] += 1

                    analyse = self.analyser_texte(texte)
                    d = analyse["details"]
                    pts_prio = len(d.get("prioritaires", [])) * 2
                    pts_sec  = len(d.get("secondaires", []))
                    pts_bud  = len(d.get("budget", []))
                    score_kw = analyse["score"]
                    _log(
                        f"         📊 Score : {pts_prio} pts prioritaires"
                        f" + {pts_sec} pts secondaires"
                        f" + {pts_bud} pts budget = {score_kw}"
                        f" (seuil={self.seuil_confiance})"
                    )

                    if analyse["mots_trouves"]:
                        bilan["docs_avec_mots_cles"] += 1
                        _log(f"         🔑 Mots trouvés : {analyse['mots_trouves']}")

                    if not analyse["pertinent"]:
                        bilan["docs_ecartes"] += 1
                        extrait_doc = _extrait_30_mots(texte) if status_callback else ""
                        _log(
                            f"         ❌ Écarté (score {score_kw} < seuil {self.seuil_confiance})"
                            + (f' | Début : "{extrait_doc}"' if extrait_doc else "")
                        )
                        continue

                    date_pub = self.extraire_date(texte=texte, url=full_url)
                    if not self.est_dans_fenetre(date_pub):
                        _log(f"         ↳ ⏭️ Hors fenêtre temporelle (date contenu) — ignoré")
                        bilan["docs_ecartes"] += 1
                        continue

                    sf = self.analyser_signaux_faibles(texte)
                    sc = self.calculer_score_composite(analyse, sf, date_pub, section_type)
                    doc = self._build_result(
                        fname, full_url, url, commune, dept, texte, analyse,
                        source_type=section_type,
                        date_pub=date_pub,
                        signaux_faibles=sf,
                        score_composite=sc,
                    )
                    _hash = hashlib.md5(texte[:500].encode()).hexdigest()
                    if _hash in seen_hashes:
                        _log(f"         ⏭️ Contenu dupliqué ignoré : {fname}")
                        continue
                    seen_hashes.add(_hash)
                    found.append(doc)
                    bilan["docs_retenus"] += 1
                    bilan["score_max"] = max(bilan["score_max"], sc["score_composite"])
                    _log(
                        f"         ✅ Retenu | score composite={sc['score_composite']}"
                        f" | {sf['maturite_emoji']} {sf['maturite_label']}"
                    )

            except requests.exceptions.Timeout:
                _log(
                    f"   [{sec_idx}/{nb_sections}] ⏱️ Timeout ({sec_timeout}s) | {section_url}",
                    "warning",
                )
            except requests.RequestException as exc:
                _log(
                    f"   [{sec_idx}/{nb_sections}] ❌ Erreur : {exc.__class__.__name__} — {str(exc)[:80]}"
                    f" | {section_url}",
                    "warning",
                )

        # ── Étape 3 : Toutes les pages HTML internes non encore visitées ─────
        html3_links = [
            urljoin(url, lk.get("href", ""))
            for lk in home_soup.find_all("a", href=True)
        ]
        html3_links = [
            u for u in dict.fromkeys(html3_links)
            if urlparse(u).netloc == base_netloc and u not in seen_urls
            and not self._is_document(u)
        ]
        nb_html3 = len(html3_links)
        for h3_idx, full_url in enumerate(html3_links, 1):
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)
            try:
                time.sleep(random.uniform(0.5, 1.0))
                hr = session.get(full_url, timeout=self.timeout)
                bilan["pages_visitees"] += 1
                if hr.status_code != 200:
                    continue
                page_soup = BeautifulSoup(hr.text, "html.parser")
                texte = self._extraire_texte_html(hr.text)
                nb_mots = len(texte.split()) if texte else 0

                if not texte or nb_mots < 50:
                    continue

                analyse = self.analyser_texte(texte)
                d = analyse["details"]
                pts_prio = len(d.get("prioritaires", [])) * 2
                pts_sec  = len(d.get("secondaires", []))
                pts_bud  = len(d.get("budget", []))
                score_kw = analyse["score"]

                if not analyse["pertinent"]:
                    bilan["docs_ecartes"] += 1
                    continue

                bilan["docs_avec_mots_cles"] += 1
                _log(
                    f"   [{h3_idx}/{nb_html3}] 🌐 HTML pertinent : {full_url}"
                    f" | {nb_mots} mots | score {pts_prio}+{pts_sec}+{pts_bud}={score_kw}"
                )

                date_pub = self.extraire_date(soup=page_soup, texte=texte, url=full_url)
                if not self.est_dans_fenetre(date_pub):
                    _log(f"      ↳ ⏭️ Hors fenêtre temporelle — ignoré")
                    bilan["docs_ecartes"] += 1
                    continue

                sf = self.analyser_signaux_faibles(texte)
                sc = self.calculer_score_composite(analyse, sf, date_pub, "generique")
                filename = os.path.basename(urlparse(full_url).path) or "page.html"
                doc = self._build_result(
                    filename, full_url, url, commune, dept, texte, analyse,
                    source_type="generique",
                    date_pub=date_pub,
                    signaux_faibles=sf,
                    score_composite=sc,
                )
                doc["document_type"] = "html"
                found.append(doc)
                bilan["docs_retenus"] += 1
                bilan["score_max"] = max(bilan["score_max"], sc["score_composite"])
                _log(f"      ✅ Retenu | score composite={sc['score_composite']}")

            except requests.RequestException:
                pass

        # ── Bilan par site ─────────────────────────────────────────────────────
        found.sort(key=lambda r: r.get("score_composite", 0), reverse=True)
        sep = "─" * 45
        _log(sep)
        _log(f"📊 BILAN [{commune}]")
        _log(f"   🌐 Pages visitées        : {bilan['pages_visitees']}")
        _log(
            f"   📄 PDFs tentés           : {bilan['pdfs_tentes']}"
            f" ({bilan['pdfs_reussis']} réussis,"
            f" {bilan['pdfs_scannes']} vides/scannés)"
        )
        _log(f"   🔑 Docs avec mots-clés   : {bilan['docs_avec_mots_cles']}")
        _log(f"   ✅ Docs retenus          : {bilan['docs_retenus']} (score ≥ {self.seuil_confiance})")
        _log(f"   ❌ Docs écartés          : {bilan['docs_ecartes']}")
        _log(f"   🏆 Score max atteint     : {bilan['score_max']} (seuil = {self.seuil_confiance})")
        _log(sep)

        return found

    def _extraire_texte_document_verbose(
        self,
        url: str,
        session: requests.Session,
        _log,
    ) -> Tuple[Optional[str], int, int]:
        """
        Télécharge et extrait le texte d'un document.
        Retourne (texte, nb_pages, nb_chars). Logs détaillés via _log.
        """
        try:
            time.sleep(random.uniform(self.delai * 0.5, self.delai))
            t0 = time.time()
            r = session.get(url, timeout=self.timeout)
            elapsed_ms = int((time.time() - t0) * 1000)

            if r.status_code != 200:
                _log(
                    f"         ❌ Téléchargement échoué HTTP {r.status_code} ({elapsed_ms} ms)",
                    "warning",
                )
                return None, 0, 0

            _log(f"         ↳ HTTP {r.status_code} | {len(r.content):,} octets | {elapsed_ms} ms")

            if url.lower().endswith(".pdf") or "pdf" in url.lower():
                import io
                nb_pages = 0
                texte = ""
                # Tentative 1 : pdfplumber
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                        nb_pages = len(pdf.pages)
                        textes = [p.extract_text() or "" for p in pdf.pages[:10]]
                    texte = "\n".join(textes).strip()
                except Exception as exc:
                    _log(f"         ⚠️ pdfplumber échoué : {exc}", "warning")
                # Tentative 2 : pymupdf si pdfplumber insuffisant
                if len(texte) < 100:
                    try:
                        import fitz
                        doc_fitz = fitz.open(stream=r.content, filetype="pdf")
                        nb_pages = nb_pages or doc_fitz.page_count
                        texte_fitz = "\n".join(
                            doc_fitz[i].get_text() for i in range(min(10, doc_fitz.page_count))
                        ).strip()
                        if len(texte_fitz) > len(texte):
                            texte = texte_fitz
                            _log(f"         ↳ pymupdf fallback : {len(texte):,} car.")
                    except Exception as exc2:
                        _log(f"         ⚠️ pymupdf échoué : {exc2}", "warning")
                nb_chars = len(texte)
                _log(f"         ↳ {nb_pages} page(s) | {nb_chars:,} caractères extraits")
                if nb_chars < 100:
                    _log(
                        f"         ⚠️ PDF potentiellement scanné (image) — {url}",
                        "warning",
                    )
                    return None, nb_pages, nb_chars
                return texte, nb_pages, nb_chars
            else:
                texte = self._extraire_texte_html(r.text, url=url)
                nb_chars = len(texte)
                _log(f"         ↳ HTML | {nb_chars:,} caractères extraits")
                return texte or None, 1, nb_chars

        except requests.RequestException as exc:
            _log(f"         ❌ Erreur téléchargement : {exc}", "warning")
            return None, 0, 0

    # ── Helpers privés ─────────────────────────────────────────────────────────

    def _get_sources_prioritaires(self, base_url: str, soup: BeautifulSoup,
                                   base_netloc: str) -> List[Tuple[str, str]]:
        """
        Retourne TOUTES les URLs de sections détectées, triées par potentiel :
        Priorité 1 : deliber, conseil, budget, marche, projet, energie, travaux, document, rapport
        Priorité 2 : actu, news, article, bulletin
        Priorité 3 : tout le reste
        """
        seen: set = set()
        # (url, stype, priorite)
        candidates: List[Tuple[str, str, int]] = []

        def _priorite(url_lower: str) -> int:
            for i, mots in enumerate(_PRIORITE_MOTS):
                if any(m in url_lower for m in mots):
                    return i  # 0 = plus haute priorité
            return len(_PRIORITE_MOTS)  # priorité basse

        for link in soup.find_all("a", href=True):
            href = link.get("href", "").strip()
            # Filtrer ancres pures (#, #main, javascript:, mailto:)
            if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
                continue
            full = urljoin(base_url, href)
            if urlparse(full).netloc != base_netloc:
                continue
            if full in seen:
                continue
            # Filtrer ancres résolues et URL racine
            parsed_full = urlparse(full)
            if parsed_full.fragment:  # contient un # après résolution
                continue
            if full.rstrip('/') == base_url.rstrip('/'):
                continue
            url_lower = full.lower()
            stype = "generique"
            for st, pat in _SECTION_PATTERNS.items():
                if pat.search(href) or pat.search(link.get_text()):
                    stype = st
                    break
            # N'inclure que les sections non-document
            if self._is_document(full):
                continue
            seen.add(full)
            candidates.append((full, stype, _priorite(url_lower)))

        # Tri : priorité croissante (0 = premier), puis ordre d'apparition
        candidates.sort(key=lambda x: x[2])
        return [(u, st) for u, st, _ in candidates]

    def _is_document(self, url: str) -> bool:
        url_lower = url.lower()
        return any(url_lower.endswith(ext) or ext in url_lower for ext in self.DOC_EXTENSIONS)

    # URLs clairement inutiles à exclure (blacklist)
    _HTML_BLACKLIST = [
        "login", "logout", "signin", "sign-in", "register",
        "cart", "panier", "checkout",
        "mailto:", "tel:", "javascript:",
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
        ".css", ".js", ".ico", ".woff", ".ttf",
        "facebook.com", "twitter.com", "instagram.com", "youtube.com",
        "linkedin.com", "google.com",
        "/feed", "/rss", "/sitemap",
    ]

    def _is_relevant_html(self, url: str) -> bool:
        url_lower = url.lower()
        return not any(b in url_lower for b in self._HTML_BLACKLIST)

    def _extraire_texte_document(
        self, url: str, session: requests.Session, log_fn
    ) -> Optional[str]:
        """Télécharge et extrait le texte d'un document (PDF/DOC)."""
        try:
            time.sleep(random.uniform(self.delai * 0.5, self.delai))
            r = session.get(url, timeout=self.timeout)
            r.raise_for_status()

            if url.lower().endswith(".pdf") or "pdf" in url.lower():
                import io
                texte = ""
                # Tentative 1 : pdfplumber
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                        textes = [p.extract_text() or "" for p in pdf.pages[:10]]
                    texte = "\n".join(textes).strip()
                except Exception as exc:
                    log_fn(f"pdfplumber échoué pour {url} : {exc}", "warning")
                # Tentative 2 : pymupdf si pdfplumber insuffisant
                if len(texte) < 100:
                    try:
                        import fitz
                        doc_fitz = fitz.open(stream=r.content, filetype="pdf")
                        texte_fitz = "\n".join(
                            doc_fitz[i].get_text() for i in range(min(10, doc_fitz.page_count))
                        ).strip()
                        if len(texte_fitz) > len(texte):
                            texte = texte_fitz
                    except Exception as exc2:
                        log_fn(f"pymupdf échoué pour {url} : {exc2}", "warning")
                if len(texte) < 100:
                    log_fn(f"⚠️ PDF potentiellement scanné (image) — {url}", "warning")
                    return None
                return texte
            else:
                return self._extraire_texte_html(r.text, url=url)

        except requests.RequestException as exc:
            log_fn(f"Erreur téléchargement {url} : {exc}", "warning")
            return None

    def _extraire_texte_html(self, html: str, url: str = "") -> str:
        """Extrait le texte utile d'une page HTML via Trafilatura (fallback BS4)."""
        texte = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            url=url or None,
        )
        if texte and len(texte) > 100:
            return texte
        # Fallback BeautifulSoup
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
        source_type: str = "generique",
        date_pub: Optional[datetime] = None,
        signaux_faibles: Optional[Dict] = None,
        score_composite: Optional[Dict] = None,
    ) -> Dict:
        sf = signaux_faibles or {}
        sc = score_composite or {"score_composite": analyse["score"], "score_details": {}}
        src_label = SOURCE_PRIORITES.get(source_type, ("Page générique", 0))[0]
        return {
            "nom_fichier": filename,
            "source_url": source_url,
            "site_url": site_url,
            "commune": commune,
            "departement": dept,
            "date_detection": datetime.now().isoformat(),
            "date_publication": date_pub.isoformat() if date_pub else None,
            "texte": texte[:50000],
            "score": analyse["score"],
            "score_composite": sc["score_composite"],
            "score_details": sc["score_details"],
            "pertinent": analyse["pertinent"],
            "mots_trouves": analyse["mots_trouves"],
            "details_mots": analyse["details"],
            "source_type": source_type,
            "source_label": src_label,
            "signaux_faibles": sf.get("signaux_trouves", {}),
            "categories_signaux": sf.get("categories", []),
            "maturite": sf.get("maturite", "reflexion"),
            "maturite_label": sf.get("maturite_label", "Réflexion"),
            "maturite_emoji": sf.get("maturite_emoji", "🟢"),
            "maturite_delai": sf.get("maturite_delai", "12+ mois"),
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
