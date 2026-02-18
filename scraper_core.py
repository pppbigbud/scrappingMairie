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

import requests
from bs4 import BeautifulSoup

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
        """
        self._reload_config()

        def _log(msg: str, level: str = "info") -> None:
            getattr(log, level)(msg)
            if status_callback:
                status_callback(msg)

        _log(f"🔍 Scraping {commune} ({url}) | fenêtre {self.fenetre_jours}j")
        session = self._make_session()
        found: List[Dict] = []
        seen_urls: set = set()
        base_netloc = urlparse(url).netloc

        # ── Étape 0 : Chargement page d'accueil ───────────────────────────────
        try:
            time.sleep(random.uniform(self.delai * 0.5, self.delai * 1.5))
            response = session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            _log(f"Erreur connexion {url} : {exc}", "warning")
            return []

        home_soup = BeautifulSoup(response.text, "html.parser")

        # ── Étape 1 : Flux RSS (priorité maximale) ────────────────────────────
        rss_entries = self.detecter_flux_rss(url, home_soup, session)
        if rss_entries:
            _log(f"📡 RSS : {len(rss_entries)} entrées trouvées")
        for entry in rss_entries:
            if not self.est_dans_fenetre(entry.get("date_publication")):
                continue
            texte = entry.get("texte", "") + " " + entry.get("titre", "")
            analyse = self.analyser_texte(texte)
            if not analyse["pertinent"]:
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

        # ── Étape 2 : Sources prioritaires (actualités, délibérations, bulletins) ──
        sources_prioritaires = self._get_sources_prioritaires(url, home_soup, base_netloc)
        for section_url, section_type in sources_prioritaires:
            if section_url in seen_urls:
                continue
            try:
                time.sleep(random.uniform(0.5, 1.2))
                r = session.get(section_url, timeout=self.timeout)
                if r.status_code != 200:
                    continue
                sub_soup = BeautifulSoup(r.text, "html.parser")
                _log(f"📂 Section {section_type} : {section_url}")

                # Liens documents dans cette section
                for link in sub_soup.find_all("a", href=True):
                    href = link.get("href", "")
                    full_url = urljoin(url, href)
                    if full_url in seen_urls:
                        continue
                    if urlparse(full_url).netloc != base_netloc:
                        continue
                    seen_urls.add(full_url)

                    if self._is_document(full_url):
                        # Filtre date sur nom de fichier avant téléchargement
                        date_fname = self.extraire_date(url=full_url)
                        if not self.est_dans_fenetre(date_fname):
                            continue
                        texte = self._extraire_texte_document(full_url, session, _log)
                        if not texte:
                            continue
                        analyse = self.analyser_texte(texte)
                        if not analyse["pertinent"]:
                            continue
                        page_soup = None
                        date_pub = self.extraire_date(soup=page_soup, texte=texte, url=full_url)
                        if not self.est_dans_fenetre(date_pub):
                            continue
                        sf = self.analyser_signaux_faibles(texte)
                        sc = self.calculer_score_composite(analyse, sf, date_pub, section_type)
                        doc = self._build_result(
                            os.path.basename(urlparse(full_url).path) or full_url,
                            full_url, url, commune, dept, texte, analyse,
                            source_type=section_type,
                            date_pub=date_pub,
                            signaux_faibles=sf,
                            score_composite=sc,
                        )
                        found.append(doc)
                        _log(f"📄 {doc['nom_fichier'][:50]} | score={sc['score_composite']} | {sf['maturite_emoji']} {sf['maturite_label']}")

            except requests.RequestException:
                pass

        # ── Étape 3 : Pages HTML pertinentes de la section ────────────────────
        for link in home_soup.find_all("a", href=True):
            full_url = urljoin(url, link.get("href", ""))
            if full_url in seen_urls:
                continue
            if urlparse(full_url).netloc != base_netloc:
                continue
            if not self._is_relevant_html(full_url):
                continue
            seen_urls.add(full_url)
            try:
                time.sleep(random.uniform(0.5, 1.0))
                hr = session.get(full_url, timeout=self.timeout)
                if hr.status_code != 200:
                    continue
                page_soup = BeautifulSoup(hr.text, "html.parser")
                texte = self._extraire_texte_html(hr.text)
                if not texte or len(texte) < 300:
                    continue
                analyse = self.analyser_texte(texte)
                if not analyse["pertinent"]:
                    continue
                date_pub = self.extraire_date(soup=page_soup, texte=texte, url=full_url)
                if not self.est_dans_fenetre(date_pub):
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
            except requests.RequestException:
                pass

        # Tri par score composite décroissant
        found.sort(key=lambda r: r.get("score_composite", 0), reverse=True)
        pertinents = [r for r in found if r.get("pertinent")]
        _log(
            f"✅ Terminé {commune} : {len(found)} docs | {len(pertinents)} pertinents "
            f"| fenêtre {self.fenetre_jours}j"
        )
        return found

    # ── Helpers privés ─────────────────────────────────────────────────────────

    def _get_sources_prioritaires(self, base_url: str, soup: BeautifulSoup,
                                   base_netloc: str) -> List[Tuple[str, str]]:
        """
        Retourne les URLs des sections à explorer, avec leur type, dans l'ordre :
        actualités > délibérations > bulletins > budget > générique.
        """
        results: List[Tuple[str, str]] = []
        seen = set()
        priority_order = ["actualites", "deliberation", "bulletin", "budget"]

        # Construire un dict type -> liste d'URLs
        typed: Dict[str, List[str]] = {k: [] for k in priority_order}

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            full = urljoin(base_url, href)
            if urlparse(full).netloc != base_netloc:
                continue
            if full in seen:
                continue
            for stype, pat in _SECTION_PATTERNS.items():
                if pat.search(href) or pat.search(link.get_text()):
                    if stype in typed:
                        typed[stype].append(full)
                        seen.add(full)
                    break

        for stype in priority_order:
            for u in list(dict.fromkeys(typed[stype]))[:5]:
                results.append((u, stype))

        return results

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
