#!/usr/bin/env python3
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 10, 'Rapport Prospection Chaufferies Biomasse - AURA 2026', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# Title
pdf.set_font('Helvetica', 'B', 20)
pdf.cell(0, 15, 'PROSPECTION CHAUFFERIES BIOMASSE', 0, 1, 'C')
pdf.set_font('Helvetica', '', 14)
pdf.cell(0, 10, 'Auvergne-Rhone-Alpes - Fevrier 2026', 0, 1, 'C')
pdf.ln(10)

# Summary
pdf.set_font('Helvetica', 'B', 14)
pdf.cell(0, 10, 'RESUME EXECUTIF', 0, 1)
pdf.set_font('Helvetica', '', 11)
pdf.multi_cell(0, 7, """
- Communes scannees : ~200 (12 departements AURA)
- Projets identifies : 140+ mentions de projets energie
- Opportunites biomasse/chaleur : 9 communes prioritaires
- Date d'extraction : 1er fevrier 2026
""")
pdf.ln(5)

# TOP 3
pdf.set_font('Helvetica', 'B', 16)
pdf.set_fill_color(255, 243, 205)
pdf.cell(0, 12, 'TOP OPPORTUNITES BIOMASSE / RESEAU CHALEUR', 0, 1, 'C', True)
pdf.ln(5)

# 1. Nivigne-et-Suran
pdf.set_font('Helvetica', 'B', 14)
pdf.set_fill_color(255, 200, 200)
pdf.cell(0, 10, '1. NIVIGNE-ET-SURAN (01) - PRIORITE HAUTE', 0, 1, '', True)
pdf.set_font('Helvetica', '', 11)
pdf.multi_cell(0, 6, """Population : 2 500 habitants
Projet : Remplacement chaufferie fioul -> chaudiere bois
Statut : Projet "largement plebiscite" - reporte mandature 2020-2026
Atout majeur : 800 hectares de forets communales sous-exploitees
Timing : Nouveau mandat 2026 = relance tres probable

CONTACTS :
- Telephone mairie : 04 74 51 70 52
- Portable Maire : 06 85 28 86 76 (RDV jeudi 11h-12h30)
- Email : mairie@nivigne-et-suran.fr
- Adresse : Place de la Mairie, 01250 Nivigne et Suran

SOURCE : https://www.nivigne-et-suran.fr/4639-bulletin-municipal-2026.htm

EXTRAIT : "Dans le registre des sujets non traites et pourtant largement plebiscites 
dans notre projet de mandature : le remplacement de notre chaufferie fioul par une 
chaudiere bois, avec la volonte de profiter de notre biomasse (bois-energie). 
Environ 800 hectares de forets communales disponibles sont largement sous-exploites."
""")
pdf.ln(5)

# 2. Le Puy-en-Velay
pdf.set_font('Helvetica', 'B', 14)
pdf.cell(0, 10, '2. LE PUY-EN-VELAY (43) - PRIORITE HAUTE', 0, 1, '', True)
pdf.set_font('Helvetica', '', 11)
pdf.multi_cell(0, 6, """Population : 18 700 habitants
Projet existant : Chaufferie biomasse en activite depuis 7 ans
Opportunite : Extension reseau chaleur / Maintenance / Modernisation
Mots-cles detectes : chaufferie, biomasse, reseau de chaleur, plan climat

CONTACTS :
- Telephone : 04 71 04 37 30
- Email guichet : guichetunique@lepuyenvelay.fr
- Email ville : contact.ville@lepuyenvelay.fr

SOURCE : https://www.lepuyenvelay.fr/archives-des-actualites-mairie-du-puy-en-velay.html

EXTRAIT : "En activite depuis 7 ans, la chaufferie biomasse du Puy-en-Velay est un 
exemple de transition energetique sur le territoire."
""")
pdf.ln(5)

pdf.add_page()

# 3. Thonon-les-Bains
pdf.set_font('Helvetica', 'B', 14)
pdf.set_fill_color(255, 200, 200)
pdf.cell(0, 10, '3. THONON-LES-BAINS (74) - PRIORITE HAUTE', 0, 1, '', True)
pdf.set_font('Helvetica', '', 11)
pdf.multi_cell(0, 6, """Population : 36 000 habitants
Projet : Reseau de chaleur urbain en developpement
Mots-cles detectes : reseau de chaleur, projet, subvention

CONTACTS :
- Site officiel : www.ville-thonon.fr
- Page projet : Section "Une Ville en mutation" -> "Reseau de chaleur urbain"

SOURCE : https://www.ville-thonon.fr
""")
pdf.ln(5)

# Autres opportunités
pdf.set_font('Helvetica', 'B', 14)
pdf.set_fill_color(200, 220, 255)
pdf.cell(0, 10, 'AUTRES OPPORTUNITES IDENTIFIEES', 0, 1, '', True)
pdf.set_font('Helvetica', '', 11)
pdf.multi_cell(0, 6, """
4. MEYLAN (38) - 18 000 hab - Reseau chaleur + Plan climat
   Source : https://www.meylan.fr

5. FERNEY-VOLTAIRE (01) - 10 000 hab - Reseau de chaleur
   Source : https://www.ferney-voltaire.fr

6. AUBENAS (07) - 12 500 hab - Reseau de chaleur
   Source : https://www.aubenas.fr

7. SAINT-MARCELLIN (38) - 7 800 hab - Chaufferie + Reseau de chaleur
   Source : https://www.saint-marcellin.fr

8. CUSSET (03) - 13 000 hab - Plaquettes forestieres
   Source : https://www.ville-cusset.com

9. ECHIROLLES (38) - 36 000 hab - Plaquettes forestieres
   Source : https://www.echirolles.fr
""")
pdf.ln(5)

# Stratégie
pdf.set_font('Helvetica', 'B', 14)
pdf.cell(0, 10, 'STRATEGIE DE PROSPECTION RECOMMANDEE', 0, 1)
pdf.set_font('Helvetica', '', 11)
pdf.multi_cell(0, 6, """
PHASE 1 (Semaine 1-2) :
- Appeler Nivigne-et-Suran (Maire : 06 85 28 86 76)
- Email Le Puy-en-Velay
- Contact Thonon service technique

PHASE 2 (Semaine 3-4) :
- Meylan - service environnement
- Ferney-Voltaire - mairie
- Aubenas - service technique

PHASE 3 (Mois 2) :
- Suivi et relances autres communes
""")

pdf.ln(10)
pdf.set_font('Helvetica', 'I', 10)
pdf.cell(0, 10, 'Rapport genere le 1er fevrier 2026 - Systeme de veille automatise', 0, 1, 'C')

pdf.output('Rapport_Prospection_Chaufferies_AURA_2026.pdf')
print('PDF genere avec succes!')
