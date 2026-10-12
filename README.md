# BÒRD PRO

SaaS de gestion pour artistes et associations du spectacle vivant.

## Démarrage local
1. `python3 -m venv .venv` puis `source .venv/bin/activate`
2. `pip install -r requirements/dev.txt`
3. `cp .env.example .env` et renseigner les valeurs
4. `docker compose up -d db`
5. `python manage.py runserver`

Documentation : dossier `docs/`.
