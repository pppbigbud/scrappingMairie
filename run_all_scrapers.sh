#!/bin/bash
echo "🚀 Lancement de tous les scrapers..."

docker run --rm -v $(pwd)/resultats:/app/resultats scraper-chaufferies python3 scraper_aura_5000plus.py
docker run --rm -v $(pwd)/resultats:/app/resultats scraper-chaufferies python3 scraper_bulletins_2026.py
docker run --rm -v $(pwd)/resultats:/app/resultats scraper-chaufferies python3 scraper_deliberations_2026.py
docker run --rm -v $(pwd)/resultats:/app/resultats scraper-chaufferies python3 scraper_niveau_pro.py

echo "✅ Tous les scrapers terminés!"
echo "📊 Résultats dans le dossier ./resultats/"
