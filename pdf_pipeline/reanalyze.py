#!/usr/bin/env python3
"""
Script de réanalyse rapide des documents avec filtrage strict
"""
import os
import json
from datetime import datetime
from ia_analyzer import analyze_pdf

def quick_reanalyze():
    """Réanalyse tous les documents avec les nouveaux critères stricts"""
    base_dir = '../data/pdf_texts/www.mairie-trevoux.fr_'
    
    # Compteurs
    total = 0
    reanalyzed = 0
    pertinent_found = 0
    
    print("🔍 Réanalyse avec filtrage strict...")
    print("=" * 50)
    
    for filename in os.listdir(base_dir):
        if filename.endswith('.json'):
            total += 1
            json_path = os.path.join(base_dir, filename)
            pdf_path = json_path.replace('.json', '')
            
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Forcer la réanalyse seulement si score élevé mais probablement faux
                current_score = data.get('ia_score', 0)
                current_pertinent = data.get('ia_pertinent', False)
                
                # Réanalyser si : score élevé OU jamais analysé
                if current_score >= 7 or current_pertinent is None:
                    print(f"🔄 Réanalyse : {filename}")
                    if analyze_pdf(pdf_path, json_path):
                        reanalyzed += 1
                        
                        # Vérifier le nouveau résultat
                        with open(json_path, 'r', encoding='utf-8') as f:
                            new_data = json.load(f)
                        if new_data.get('ia_pertinent', False):
                            pertinent_found += 1
                            print(f"✅ PERTINENT : {filename} (score: {new_data.get('ia_score', 0)})")
                        else:
                            print(f"❌ Non pertinent : {filename} (score: {new_data.get('ia_score', 0)})")
                else:
                    print(f"⏭️  Ignoré : {filename} (score: {current_score})")
                    
            except Exception as e:
                print(f"❌ Erreur {filename}: {e}")
    
    print("=" * 50)
    print(f"📊 Résultats :")
    print(f"   Total documents : {total}")
    print(f"   Réanalysés : {reanalyzed}")
    print(f"   Pertinents trouvés : {pertinent_found}")
    print(f"   Taux de pertinence : {pertinent_found/total*100:.1f}%")

if __name__ == "__main__":
    quick_reanalyze()
