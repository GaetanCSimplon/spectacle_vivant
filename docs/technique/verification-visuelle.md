# Vérification visuelle dans un vrai navigateur

Créée le 2026-11-16. Les tests Django vérifient le HTML renvoyé, pas ce que l'utilisateur voit (chevauchements, texte écrasé, clic qui ne fait rien). Cette méthode lance un **vrai Chromium** sur un serveur de test et prend des captures. Elle a trouvé un défaut que les 2 600 tests ne voyaient pas (texte des alertes écrasé à 375 px, #376).

**Rien de cette méthode n'est dans le dépôt ni dans `requirements/`** : Playwright est installé dans un dossier temporaire. Si on veut la garder en continu (CI), c'est une décision à prendre (ajout de Playwright aux dépendances de développement).

## Préparer (une fois par session)
```bash
# 1. Playwright dans un dossier à part (jamais dans requirements/). La 1.46 fonctionne avec le Chromium déjà en cache.
pip install --target /tmp/pwlib playwright==1.46.0
ls ~/.cache/ms-playwright          # ex. chromium-1134 : c'est ce Chromium qu'on lance
# 2. CSS à jour (sinon les classes nouvelles n'existent pas dans la capture)
python manage.py tailwind build
```
Si `ms-playwright` est vide : `PYTHONPATH=/tmp/pwlib python -m playwright install chromium` (téléchargement).

## Écrire un scénario
Un fichier **hors du dépôt** (ex. `/tmp/test_visual.py`) qui utilise la fixture `live_server` de pytest-django. Le même schéma sert à toute page :

```python
import sys; sys.path.insert(0, "/tmp/pwlib")
import pytest
from django.urls import reverse
from playwright.sync_api import sync_playwright
from apps.gigs.factories import GigFactory
from apps.tenants.factories import MembershipFactory

CHROME = "/home/<user>/.cache/ms-playwright/chromium-1134/chrome-linux/chrome"

@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("size", [(1440, 900), (375, 800)])   # ordinateur, mobile
def test_shots(live_server, client, size, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    m = MembershipFactory(); client.force_login(m.user)        # connexion : on reprend le cookie de session
    cookie = client.cookies["sessionid"].value
    gig = GigFactory(tenant=m.tenant, price="0.00")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME)          # chemin explicite : la version de Playwright cherche une autre révision
        ctx = b.new_context(viewport={"width": size[0], "height": size[1]})
        ctx.add_cookies([{"name": "sessionid", "value": cookie, "url": live_server.url}])
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(live_server.url + reverse("gigs:detail", args=[gig.pk]))
        page.wait_for_selector("#radar-button button")         # le bouton arrive par HTMX
        page.screenshot(path="/tmp/shots/detail.png")
        print(page.locator("#radar-button button").bounding_box(), errors)   # mesures : chevauchements, erreurs JS
        b.close()
```

## Lancer
```bash
pytest /tmp/test_visual.py -c pyproject.toml --rootdir=. -s -q -p no:cacheprovider
```
Puis lire les images (`Read` sur les `.png`). Regarder : chevauchements (mesurer les boîtes, ne pas se fier à l'œil), texte coupé ou écrasé à 375 px, couleurs et contrastes, erreurs JavaScript (liste `errors`).

## Limites
- Les statiques viennent de `static/css/tailwind.css` : refaire `tailwind build` après chaque changement de gabarit.
- Pas de données réalistes : seulement ce que le scénario crée (utiliser les factories, ou la commande `seed_demo`).
- Ne remplace ni les tests Django ni l'audit axe-core (`audit-accessibilite.md`) ; clavier, lecteur d'écran et zoom 200 % restent des contrôles manuels.
