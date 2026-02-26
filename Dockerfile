# ═══════════════════════════════════════════════════════════
# ElectroSecure Platform — Dockerfile Railway
# ═══════════════════════════════════════════════════════════

FROM python:3.11-slim

# Variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Installer PostgreSQL client
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        postgresql-client \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer requirements
COPY requirements/base.txt requirements/
RUN pip install --no-cache-dir -r requirements/base.txt && \
    pip install --no-cache-dir \
        gunicorn==21.2.0 \
        dj-database-url==2.1.0 \
        whitenoise==6.6.0 \
        psycopg2-binary==2.9.9

# Copier le code
COPY . .

# Créer dossiers
RUN mkdir -p staticfiles media logs

# Collecter statiques
RUN python manage.py collectstatic --noinput || true

# Port
EXPOSE 8000

# Commande SIMPLE (Railway gère les migrations via nixpacks)
CMD gunicorn config.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info