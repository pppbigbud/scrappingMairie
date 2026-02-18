import os
import json
from glob import glob

def build_global_index(base_dir='data/pdf_texts'):
    index = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        data['json_path'] = path
                        index.append(data)
                except Exception as e:
                    print(f"[INDEX] Erreur lecture {path} : {e}")
    # Sauvegarde index global
    out_path = os.path.join(base_dir, 'index_global.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"[INDEX] Index global généré : {out_path}")
    return index

if __name__ == "__main__":
    build_global_index()
