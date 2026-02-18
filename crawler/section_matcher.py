from rapidfuzz import fuzz

KEYWORDS = ['bulletin', 'publication', 'conseil', 'délibération', 'marché public']

# Détecte si le texte ou l'URL d'un lien correspond à une section pertinente

def is_section_relevant(text, href):
    text = (text or '').lower()
    href = (href or '').lower()
    for k in KEYWORDS:
        if fuzz.partial_ratio(text, k) > 70 or fuzz.partial_ratio(href, k) > 70:
            return True
    return False
