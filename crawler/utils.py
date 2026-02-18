from urllib.parse import urljoin

def normalize_url(base, href):
    """Retourne une URL absolue à partir d'un lien relatif."""
    return urljoin(base, href)
