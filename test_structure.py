#!/usr/bin/env python3
"""
Script de vérification de la structure du projet ElectroSecure.
Teste la cohérence sans avoir besoin d'installer les dépendances.

Usage:
    python test_structure.py
"""

import os
import sys
from pathlib import Path

# Couleurs pour la sortie
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check(name, condition, details=""):
    """Affiche le résultat d'un test."""
    status = f"{GREEN}✓{RESET}" if condition else f"{RED}✗{RESET}"
    print(f"{status} {name}")
    if details and not condition:
        print(f"  {YELLOW}→{RESET} {details}")
    return condition

def main():
    base_dir = Path(__file__).parent
    os.chdir(base_dir)
    
    print(f"\n{BLUE}═══ ElectroSecure Platform — Vérification de structure ═══{RESET}\n")
    
    results = []
    
    # ── Fichiers racine ──────────────────────────────────────
    print(f"{BLUE}Fichiers racine :{RESET}")
    results.append(check("manage.py", (base_dir / "manage.py").exists()))
    results.append(check(".env.example", (base_dir / ".env.example").exists()))
    
    # ── Config ───────────────────────────────────────────────
    print(f"\n{BLUE}Configuration (config/) :{RESET}")
    config = base_dir / "config"
    results.append(check("config/__init__.py", (config / "__init__.py").exists()))
    results.append(check("config/settings/base.py", (config / "settings" / "base.py").exists()))
    results.append(check("config/settings/development.py", (config / "settings" / "development.py").exists()))
    results.append(check("config/settings/production.py", (config / "settings" / "production.py").exists()))
    results.append(check("config/urls.py", (config / "urls.py").exists()))
    results.append(check("config/wsgi.py", (config / "wsgi.py").exists()))
    results.append(check("config/asgi.py", (config / "asgi.py").exists()))
    results.append(check("config/celery.py", (config / "celery.py").exists()))
    
    # ── Core ─────────────────────────────────────────────────
    print(f"\n{BLUE}Module core/ :{RESET}")
    core = base_dir / "core"
    results.append(check("core/models.py", (core / "models.py").exists()))
    results.append(check("core/constants.py", (core / "constants.py").exists()))
    results.append(check("core/validators.py", (core / "validators.py").exists()))
    results.append(check("core/permissions.py", (core / "permissions.py").exists()))
    results.append(check("core/exceptions.py", (core / "exceptions.py").exists()))
    results.append(check("core/mixins.py", (core / "mixins.py").exists()))
    
    # ── Apps ─────────────────────────────────────────────────
    print(f"\n{BLUE}Applications :{RESET}")
    apps = base_dir / "apps"
    
    # Authentication
    auth = apps / "authentication"
    results.append(check("apps/authentication/models.py", (auth / "models.py").exists()))
    results.append(check("apps/authentication/serializers.py", (auth / "serializers.py").exists()))
    results.append(check("apps/authentication/views.py", (auth / "views.py").exists()))
    results.append(check("apps/authentication/urls.py", (auth / "urls.py").exists()))
    results.append(check("apps/authentication/tasks.py", (auth / "tasks.py").exists()))
    
    # Cable routing
    cables = apps / "electrical" / "cable_routing"
    results.append(check("electrical/cable_routing/models.py", (cables / "models.py").exists()))
    results.append(check("electrical/cable_routing/services/routing_engine.py", 
                        (cables / "services" / "routing_engine.py").exists()))
    
    # Connections
    conn = apps / "electrical" / "connections"
    results.append(check("electrical/connections/models.py", (conn / "models.py").exists()))
    results.append(check("electrical/connections/services/validation_service.py",
                        (conn / "services" / "validation_service.py").exists()))
    
    # Schematics
    schem = apps / "electrical" / "schematics"
    results.append(check("electrical/schematics/models.py", (schem / "models.py").exists()))
    results.append(check("electrical/schematics/services/diagram_generator.py",
                        (schem / "services" / "diagram_generator.py").exists()))
    
    # Devices
    devices = apps / "devices"
    results.append(check("devices/models.py", (devices / "models.py").exists()))
    results.append(check("devices/serializers.py", (devices / "serializers.py").exists()))
    results.append(check("devices/tasks.py", (devices / "tasks.py").exists()))
    results.append(check("devices/services/scan_service.py",
                        (devices / "services" / "scan_service.py").exists()))
    
    # ── Vérification syntaxe Python ─────────────────────────
    print(f"\n{BLUE}Vérification syntaxe Python :{RESET}")
    
    files_to_check = [
        "config/settings/base.py",
        "config/urls.py",
        "config/celery.py",
        "core/models.py",
        "apps/authentication/models.py",
        "apps/devices/models.py",
    ]
    
    for file_path in files_to_check:
        full_path = base_dir / file_path
        if full_path.exists():
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), str(full_path), 'exec')
                results.append(check(f"Syntaxe {file_path}", True))
            except SyntaxError as e:
                results.append(check(f"Syntaxe {file_path}", False, str(e)))
        else:
            results.append(check(f"Syntaxe {file_path}", False, "Fichier absent"))
    
    # ── Résumé ───────────────────────────────────────────────
    print(f"\n{BLUE}═══════════════════════════════════════════════════════{RESET}")
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"\n{GREEN if failed == 0 else RED}Résultat : {passed}/{total} tests passés{RESET}")
    
    if failed > 0:
        print(f"{RED}{failed} erreur(s) détectée(s){RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}✅ Structure du projet correcte !{RESET}")
        print(f"\n{YELLOW}Prochaines étapes :{RESET}")
        print("  1. Activer venv + installer requirements/")
        print("  2. python manage.py migrate")
        print("  3. python manage.py createsuperuser")
        print("  4. python manage.py runserver")
        sys.exit(0)

if __name__ == '__main__':
    main()