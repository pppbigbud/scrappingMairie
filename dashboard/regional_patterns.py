"""
Regional and departmental pattern customization
Adds specific patterns for different French regions and departments
"""

import re
from typing import List

# Regional patterns by department
REGIONAL_PATTERNS = {
    '01': {  # Ain
        'name': 'Ain',
        'patterns': [
            r'.*Bourg.*Bresse.*',
            r'.*Oyonnax.*',
            r'.*Trévoux.*',
            r'.*Nivigne.*',
            r'.*Bugey.*',
        ]
    },
    '63': {  # Puy-de-Dôme
        'name': 'Puy-de-Dôme',
        'patterns': [
            r'.*Clermont.*',
            r'.*Riom.*',
            r'.*Thiers.*',
            r'.*Issoire.*',
            r'.*Auvergne.*',
        ]
    },
    '69': {  # Rhône
        'name': 'Rhône',
        'patterns': [
            r'.*Lyon.*',
            r'.*Villeurbanne.*',
            r'.*Vénissieux.*',
            r'.*Caluire.*',
            r'.*Métropole.*Lyon.*',
        ]
    },
}

# Common municipal document keywords by type
DOCUMENT_TYPE_PATTERNS = {
    'deliberations': [
        r'^DL[-_].*',
        r'^DEL[-_].*',
        r'.*[Dd][ée]lib[ée]ration.*',
        r'.*[-_]DL[-_].*',
    ],
    'conseil_municipal': [
        r'^CM[-_].*',
        r'.*[Cc]onseil.*[Mm]unicipal.*',
        r'.*[-_]CM[-_].*',
    ],
    'bulletins': [
        r'^BM[-_].*',
        r'^BMO[-_].*',
        r'.*[Bb]ulletin.*',
        r'.*[Mm]agazine.*[Mm]unicipal.*',
        r'.*[Ii]nfo.*[A-Z][a-z]+.*',
    ],
    'budget': [
        r'.*[Bb]udget.*',
        r'.*[Cc]ompte.*[Aa]dministratif.*',
        r'.*CA[-_]\d{4}.*',
    ],
    'energy': [
        r'.*[Bb]iomasse.*',
        r'.*[Cc]haudi[èe]re.*[Bb]ois.*',
        r'.*[Rr][ée]seau.*[Cc]haleur.*',
        r'.*[Tt]ransition.*[ÉéEe]nerg[ée]tique.*',
        r'.*PCAET.*',
        r'.*[Pp]lan.*[Cc]limat.*',
    ]
}

def get_patterns_for_department(dept_code: str, include_base: bool = True) -> List[str]:
    """
    Get document patterns for a specific department
    
    Args:
        dept_code: Department code (e.g., '63', '69')
        include_base: Whether to include base patterns
    
    Returns:
        List of regex patterns
    """
    patterns = []
    
    # Add base patterns if requested
    if include_base:
        for doc_type, type_patterns in DOCUMENT_TYPE_PATTERNS.items():
            patterns.extend(type_patterns)
    
    # Add regional patterns
    if dept_code in REGIONAL_PATTERNS:
        regional_data = REGIONAL_PATTERNS[dept_code]
        patterns.extend(regional_data['patterns'])
    
    return patterns

def get_patterns_for_city(city_name: str, include_base: bool = True) -> List[str]:
    """
    Get document patterns for a specific city
    
    Args:
        city_name: City name (e.g., 'Clermont-Ferrand')
        include_base: Whether to include base patterns
    
    Returns:
        List of regex patterns including city-specific ones
    """
    patterns = []
    
    # Add base patterns
    if include_base:
        for doc_type, type_patterns in DOCUMENT_TYPE_PATTERNS.items():
            patterns.extend(type_patterns)
    
    # Add city-specific pattern
    # Remove accents and special chars for pattern
    import unicodedata
    normalized_city = unicodedata.normalize('NFKD', city_name)
    normalized_city = ''.join([c for c in normalized_city if not unicodedata.combining(c)])
    
    # Create flexible city pattern
    city_pattern = f'.*{re.escape(normalized_city)}.*'
    patterns.append(city_pattern)
    
    # Also add pattern without hyphens/spaces
    city_compact = normalized_city.replace('-', '').replace(' ', '')
    if city_compact != normalized_city:
        patterns.append(f'.*{re.escape(city_compact)}.*')
    
    return patterns

def get_energy_focused_patterns() -> List[str]:
    """Get patterns specifically for energy/biomass projects"""
    return DOCUMENT_TYPE_PATTERNS['energy']

def add_custom_pattern(dept_code: str, pattern: str):
    """
    Add a custom pattern for a department
    
    Args:
        dept_code: Department code
        pattern: Regex pattern to add
    """
    if dept_code not in REGIONAL_PATTERNS:
        REGIONAL_PATTERNS[dept_code] = {
            'name': f'Département {dept_code}',
            'patterns': []
        }
    
    if pattern not in REGIONAL_PATTERNS[dept_code]['patterns']:
        REGIONAL_PATTERNS[dept_code]['patterns'].append(pattern)

def get_all_patterns(dept_code: str = None, city_name: str = None, 
                     focus_energy: bool = True) -> List[str]:
    """
    Get comprehensive pattern list based on context
    
    Args:
        dept_code: Optional department code for regional patterns
        city_name: Optional city name for city-specific patterns
        focus_energy: Whether to prioritize energy-related patterns
    
    Returns:
        Comprehensive list of patterns
    """
    patterns = []
    
    # Base patterns
    for doc_type, type_patterns in DOCUMENT_TYPE_PATTERNS.items():
        patterns.extend(type_patterns)
    
    # Regional patterns
    if dept_code:
        dept_patterns = get_patterns_for_department(dept_code, include_base=False)
        patterns.extend(dept_patterns)
    
    # City patterns
    if city_name:
        city_patterns = get_patterns_for_city(city_name, include_base=False)
        patterns.extend(city_patterns)
    
    # Energy focus (move to front for priority)
    if focus_energy:
        energy_patterns = get_energy_focused_patterns()
        # Remove duplicates and put energy patterns first
        patterns = energy_patterns + [p for p in patterns if p not in energy_patterns]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_patterns = []
    for pattern in patterns:
        if pattern not in seen:
            seen.add(pattern)
            unique_patterns.append(pattern)
    
    return unique_patterns
