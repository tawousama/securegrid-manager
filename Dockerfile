# Utiliser Python 3.11
FROM python:3.11-slim

# Ne pas mettre les fichiers .pyc en cache
ENV PYTHONUNBUFFERED=1

# Répertoire de travail
WORKDIR /app

# Installer PostgreSQL et dépendances
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Copier les requirements
COPY requirements/base.txt requirements/

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements/base.txt && \
    pip install --no-cache-dir gunicorn dj-database-url whitenoise

# Copier tout le code
COPY . .

# Collecter les fichiers statiques
RUN python manage.py collectstatic --noinput || true

# Port par défaut
EXPOSE 8000

# Commande de démarrage
CMD python manage.py migrate && \
    gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2
