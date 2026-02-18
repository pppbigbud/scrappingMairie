FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier tous les fichiers
COPY . .

# Installer les dépendances Python
RUN pip install --no-cache-dir \
    requests \
    beautifulsoup4 \
    pandas \
    lxml \
    openpyxl

# Exposer le port pour l'API Flask (app.py)
EXPOSE 5000

# Commande par défaut
CMD ["python3", "app.py"]
