#!/usr/bin/env python3
"""
Backend Flask pour l'application de veille chaufferie
API REST pour lancer le scraping et retourner les résultats
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import sys
import os

# Ajouter le dossier courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper_profond import ScraperProfond

app = Flask(__name__)
CORS(app)  # Autoriser les requêtes cross-origin

# HTML de l'application (pour l'instant inline, plus tard séparé)
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Veille Chaufferie - Scraping en direct</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            padding: 40px 20px;
        }
        
        header h1 {
            font-size: 3em;
            background: linear-gradient(90deg, #e94560, #ff6b6b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        
        header p {
            color: #a0a0a0;
            font-size: 1.2em;
        }
        
        .search-panel {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #e94560;
            font-weight: 600;
        }
        
        .form-group select, .form-group input {
            width: 100%;
            padding: 12px 15px;
            border-radius: 10px;
            border: 2px solid rgba(233, 69, 96, 0.3);
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 1em;
            transition: all 0.3s;
        }
        
        .form-group select:focus, .form-group input:focus {
            outline: none;
            border-color: #e94560;
        }
        
        .btn-scrape {
            background: linear-gradient(90deg, #e94560, #ff6b6b);
            color: white;
            border: none;
            padding: 15px 50px;
            font-size: 1.2em;
            font-weight: bold;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s;
            display: block;
            margin: 0 auto;
        }
        
        .btn-scrape:hover {
            transform: scale(1.05);
            box-shadow: 0 10px 30px rgba(233, 69, 96, 0.4);
        }
        
        .btn-scrape:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        #loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        
        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(233, 69, 96, 0.3);
            border-top-color: #e94560;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
        }
        
        .results-count {
            font-size: 1.5em;
        }
        
        .results-count span {
            color: #e94560;
            font-weight: bold;
        }
        
        .results-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
            gap: 20px;
        }
        
        .result-card {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            overflow: hidden;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s;
        }
        
        .result-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            border-color: #e94560;
        }
        
        .card-header {
            background: linear-gradient(90deg, rgba(233, 69, 96, 0.3), rgba(255, 107, 107, 0.3));
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .card-header.forte {
            background: linear-gradient(90deg, rgba(46, 204, 113, 0.3), rgba(39, 174, 96, 0.3));
        }
        
        .commune-name {
            font-size: 1.3em;
            font-weight: bold;
        }
        
        .confidence-badge {
            background: rgba(0,0,0,0.3);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8em;
        }
        
        .card-body {
            padding: 20px;
        }
        
        .card-meta {
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        .meta-item {
            display: flex;
            align-items: center;
            gap: 5px;
            color: #a0a0a0;
            font-size: 0.9em;
        }
        
        .card-title {
            font-size: 1.1em;
            margin-bottom: 10px;
            line-height: 1.4;
        }
        
        .keywords {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 15px 0;
        }
        
        .keyword {
            background: rgba(233, 69, 96, 0.2);
            color: #e94560;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
        }
        
        .card-link {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            color: #e94560;
            text-decoration: none;
            margin-top: 10px;
            font-weight: 500;
        }
        
        .card-link:hover {
            text-decoration: underline;
        }
        
        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: #a0a0a0;
        }
        
        .no-results-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        
        footer {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .log-console {
            background: rgba(0,0,0,0.5);
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            max-height: 200px;
            overflow-y: auto;
            display: none;
        }
        
        .log-line {
            margin: 3px 0;
            color: #888;
        }
        
        .log-line.error { color: #e94560; }
        .log-line.success { color: #2ecc71; }
        .log-line.info { color: #3498db; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔥 Veille Chaufferie</h1>
            <p>Scraping temps réel des délibérations municipales</p>
        </header>
        
        <div class="search-panel">
            <form id="searchForm">
                <div class="form-grid">
                    <div class="form-group">
                        <label>📍 Département</label>
                        <select id="departement" name="departement">
                            <option value="63" selected>Puy-de-Dôme (63)</option>
                            <option value="03">Allier (03)</option>
                            <option value="15">Cantal (15)</option>
                            <option value="43">Haute-Loire (43)</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>🏘️ Taille des communes</label>
                        <select id="taille" name="taille">
                            <option value="toutes" selected>Toutes tailles</option>
                            <option value="petite">Petite (< 2000 hab)</option>
                            <option value="moyenne">Moyenne (2000-10000 hab)</option>
                            <option value="grande">Grande (> 10000 hab)</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>🔍 Termes de recherche</label>
                        <input type="text" id="query" name="query" 
                               placeholder="chaufferie, biomasse, chaudière bois..."
                               value="chaufferie biomasse">
                    </div>
                </div>
                
                <button type="submit" class="btn-scrape" id="btnScrape">
                    🚀 Lancer le scraping
                </button>
            </form>
            
            <div id="logConsole" class="log-console"></div>
        </div>
        
        <div id="loading">
            <div class="spinner"></div>
            <p>Scraping en cours... Ça peut prendre 30-60 secondes</p>
        </div>
        
        <div id="results"></div>
        
        <footer>
            <p>🤖 Powered by Marvin | Données issues de data.gouv.fr</p>
        </footer>
    </div>
    
    <script>
        const API_URL = window.location.origin + '/api/scrape';
        
        document.getElementById('searchForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const btn = document.getElementById('btnScrape');
            const loading = document.getElementById('loading');
            const results = document.getElementById('results');
            const logConsole = document.getElementById('logConsole');
            
            // UI loading state
            btn.disabled = true;
            btn.textContent = '⏳ Scraping en cours...';
            loading.style.display = 'block';
            results.innerHTML = '';
            logConsole.style.display = 'block';
            logConsole.innerHTML = '<div class="log-line info">🚀 Démarrage du scraping...</div>';
            
            const formData = {
                departement: document.getElementById('departement').value,
                taille: document.getElementById('taille').value,
                query: document.getElementById('query').value
            };
            
            try {
                addLog('📡 Connexion au serveur...', 'info');
                
                const response = await fetch(API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                
                if (!response.ok) {
                    throw new Error(`Erreur HTTP: ${response.status}`);
                }
                
                const data = await response.json();
                addLog(`✅ ${data.results.length} opportunités trouvées !`, 'success');
                
                displayResults(data.results);
                
            } catch (error) {
                console.error('Erreur:', error);
                addLog(`❌ Erreur: ${error.message}`, 'error');
                results.innerHTML = `
                    <div class="no-results">
                        <div class="no-results-icon">😢</div>
                        <h3>Erreur lors du scraping</h3>
                        <p>${error.message}</p>
                        <p style="margin-top: 15px; font-size: 0.9em;">
                            Vérifie que le serveur Flask est démarré (python3 app.py)
                        </p>
                    </div>
                `;
            } finally {
                btn.disabled = false;
                btn.textContent = '🚀 Lancer le scraping';
                loading.style.display = 'none';
            }
        });
        
        function addLog(message, type = 'info') {
            const logConsole = document.getElementById('logConsole');
            const line = document.createElement('div');
            line.className = `log-line ${type}`;
            line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            logConsole.appendChild(line);
            logConsole.scrollTop = logConsole.scrollHeight;
        }
        
        function displayResults(opportunites) {
            const container = document.getElementById('results');
            
            if (opportunites.length === 0) {
                container.innerHTML = `
                    <div class="no-results">
                        <div class="no-results-icon">🔍</div>
                        <h3>Aucune opportunité trouvée</h3>
                        <p>Essayez avec d'autres termes de recherche</p>
                    </div>
                `;
                return;
            }
            
            const forteCount = opportunites.filter(o => o.confiance === 'forte').length;
            
            let html = `
                <div class="results-header">
                    <div class="results-count">
                        📊 <span>${opportunites.length}</span> opportunité(s) trouvée(s)
                    </div>
                    <div style="color: #a0a0a0;">
                        🔴 ${forteCount} forte confiance | 🟠 ${opportunites.length - forteCount} moyenne
                    </div>
                </div>
                <div class="results-grid">
            `;
            
            opportunites.forEach(opp => {
                const confianceClass = opp.confiance === 'forte' ? 'forte' : '';
                const motsCles = opp.mots_cles.map(k => `<span class="keyword">${k}</span>`).join('');
                
                html += `
                    <div class="result-card">
                        <div class="card-header ${confianceClass}">
                            <div class="commune-name">📍 ${opp.commune}</div>
                            <div class="confidence-badge">${opp.confiance.toUpperCase()}</div>
                        </div>
                        <div class="card-body">
                            <div class="card-meta">
                                <div class="meta-item">📅 ${formatDate(opp.date_publication)}</div>
                                <div class="meta-item">🏛️ ${opp.departement}</div>
                            </div>
                            <div class="card-title">${opp.titre}</div>
                            <div class="keywords">${motsCles}</div>
                            <p style="color: #888; font-size: 0.9em; margin-top: 10px;">
                                ${opp.description.substring(0, 150)}...
                            </p>
                            <a href="${opp.url_source}" target="_blank" class="card-link">
                                🔗 Voir la source sur data.gouv.fr →
                            </a>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            container.innerHTML = html;
        }
        
        function formatDate(dateStr) {
            if (!dateStr || dateStr === 'Non daté') return 'Date non précisée';
            try {
                const date = new Date(dateStr);
                return date.toLocaleDateString('fr-FR');
            } catch {
                return dateStr;
            }
        }
    </script>
</body>
</html>'''

@app.route('/')
def index():
    """Page principale avec le formulaire"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """API pour lancer le scraping"""
    try:
        data = request.get_json()
        
        departement = data.get('departement', '63')
        taille = data.get('taille', 'moyenne')
        query = data.get('query', 'chaufferie biomasse')
        
        print(f"🔥 Scraping demandé: dept={departement}, taille={taille}, query={query}")
        
        # Lancer le scraping NATIONAL
        scraper = ScraperProfond()
        resultats = scraper.lancer_veille_nationale(taille=taille)
        
        # Convertir en JSON
        results_json = [{
            'commune': r.commune,
            'code_insee': '',
            'departement': r.departement,
            'date_publication': r.date,
            'titre': r.titre,
            'description': r.contenu,
            'mots_cles': r.mots_cles,
            'url_source': r.url_source,
            'confiance': r.confiance
        } for r in resultats]
        
        return jsonify({
            'success': True,
            'count': len(results_json),
            'results': results_json
        })
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({'status': 'ok', 'service': 'veille-chaufferie'})

if __name__ == '__main__':
    print("🚀 Démarrage du serveur Flask...")
    print("📍 Accès: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)