"""
Cities database loader - Uses simplified INSEE data for French municipalities
"""

import json
import os
from typing import List, Dict, Optional

# Simplified cities database with major French cities
# In production, this would load from INSEE official data
CITIES_DATA = {
    '01': [  # Ain
        {'name': 'Bourg-en-Bresse', 'code': '01053', 'population': 41661},
        {'name': 'Oyonnax', 'code': '01283', 'population': 22466},
        {'name': 'Bellegarde-sur-Valserine', 'code': '01034', 'population': 12445},
        {'name': 'Ambérieu-en-Bugey', 'code': '01004', 'population': 14463},
        {'name': 'Trévoux', 'code': '01427', 'population': 7112},
        {'name': 'Miribel', 'code': '01249', 'population': 9613},
        {'name': 'Meximieux', 'code': '01244', 'population': 7786},
        {'name': 'Lagnieu', 'code': '01206', 'population': 7268},
        {'name': 'Gex', 'code': '01173', 'population': 12748},
        {'name': 'Ferney-Voltaire', 'code': '01160', 'population': 10065},
    ],
    '63': [  # Puy-de-Dôme
        {'name': 'Clermont-Ferrand', 'code': '63113', 'population': 147284},
        {'name': 'Riom', 'code': '63300', 'population': 20464},
        {'name': 'Cournon-d\'Auvergne', 'code': '63124', 'population': 20097},
        {'name': 'Issoire', 'code': '63178', 'population': 14291},
        {'name': 'Thiers', 'code': '63430', 'population': 11486},
        {'name': 'Pont-du-Château', 'code': '63284', 'population': 12489},
        {'name': 'Gerzat', 'code': '63164', 'population': 10660},
        {'name': 'Aubière', 'code': '63014', 'population': 9162},
        {'name': 'Cébazat', 'code': '63063', 'population': 8745},
        {'name': 'Chamalières', 'code': '63075', 'population': 7814},
        {'name': 'Beaumont', 'code': '63032', 'population': 11284},
        {'name': 'Ambert', 'code': '63003', 'population': 6916},
        {'name': 'Saint-Éloy-les-Mines', 'code': '63323', 'population': 7730},
        {'name': 'Le Cendre', 'code': '63063', 'population': 5403},
        {'name': 'Lempdes', 'code': '63193', 'population': 8514},
    ],
    '69': [  # Rhône
        {'name': 'Lyon', 'code': '69123', 'population': 518635},
        {'name': 'Villeurbanne', 'code': '69266', 'population': 151797},
        {'name': 'Vénissieux', 'code': '69259', 'population': 67782},
        {'name': 'Saint-Priest', 'code': '69290', 'population': 43366},
        {'name': 'Caluire-et-Cuire', 'code': '69034', 'population': 42671},
        {'name': 'Bron', 'code': '69029', 'population': 39443},
        {'name': 'Meyzieu', 'code': '69282', 'population': 32336},
        {'name': 'Rillieux-la-Pape', 'code': '69286', 'population': 30476},
        {'name': 'Décines-Charpieu', 'code': '69275', 'population': 27814},
        {'name': 'Tassin-la-Demi-Lune', 'code': '69244', 'population': 23173},
        {'name': 'Sainte-Foy-lès-Lyon', 'code': '69202', 'population': 22453},
        {'name': 'Oullins', 'code': '69149', 'population': 26118},
        {'name': 'Vaulx-en-Velin', 'code': '69256', 'population': 51729},
        {'name': 'Givors', 'code': '69091', 'population': 20118},
        {'name': 'Mions', 'code': '69282', 'population': 12434},
        {'name': 'Écully', 'code': '69081', 'population': 18887},
        {'name': 'Francheville', 'code': '69089', 'population': 14171},
        {'name': 'Saint-Genis-Laval', 'code': '69204', 'population': 21408},
    ],
}

def get_cities_by_department(dept_code: str, min_population: int = 0) -> List[Dict]:
    """
    Get list of cities for a given department with population filter
    
    Args:
        dept_code: Department code (e.g., '63', '69', '01')
        min_population: Minimum population threshold
    
    Returns:
        List of city dictionaries with name, code, and population
    """
    cities = CITIES_DATA.get(dept_code, [])
    
    if min_population > 0:
        cities = [city for city in cities if city['population'] >= min_population]
    
    return cities

def get_department_name(dept_code: str) -> str:
    """Get department name from code"""
    dept_names = {
        '01': 'Ain',
        '63': 'Puy-de-Dôme',
        '69': 'Rhône',
    }
    return dept_names.get(dept_code, f'Département {dept_code}')

def normalize_city_name(city_name: str) -> str:
    """
    Normalize city name for URL generation
    - Remove accents
    - Convert to lowercase
    - Replace spaces with hyphens
    - Remove apostrophes
    """
    import unicodedata
    
    # Remove accents
    nfkd = unicodedata.normalize('NFKD', city_name)
    normalized = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    
    # Lowercase and replace special chars
    normalized = normalized.lower()
    normalized = normalized.replace(' ', '-')
    normalized = normalized.replace('\'', '-')
    normalized = normalized.replace('œ', 'oe')
    
    return normalized

def get_all_departments() -> List[str]:
    """Get list of all available department codes"""
    return list(CITIES_DATA.keys())
