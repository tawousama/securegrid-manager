.PHONY: help install migrate test run shell clean format lint

help:
	@echo "Commandes disponibles:"
	@echo "  install     - Installer les dépendances"
	@echo "  migrate     - Appliquer les migrations"
	@echo "  test        - Lancer les tests"
	@echo "  run         - Lancer le serveur de développement"
	@echo "  shell       - Ouvrir le shell Django"
	@echo "  clean       - Nettoyer les fichiers temporaires"
	@echo "  format      - Formater le code avec black"
	@echo "  lint        - Vérifier le code avec flake8"
	@echo "  celery      - Lancer Celery worker"

install:
	pip install -r requirements/development.txt

migrate:
	python manage.py makemigrations
	python manage.py migrate

test:
	pytest

run:
	python manage.py runserver

shell:
	python manage.py shell_plus

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/

format:
	black apps/ core/ config/
	isort apps/ core/ config/

lint:
	flake8 apps/ core/ config/
	pylint apps/ core/ config/

celery:
	celery -A config worker -l info

celery-beat:
	celery -A config beat -l info

superuser:
	python manage.py createsuperuser

collectstatic:
	python manage.py collectstatic --noinput