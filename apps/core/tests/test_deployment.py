"""The files and commands the deployment relies on (Scalingo)."""

import json
import os
import re
import stat
from pathlib import Path

import pytest
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import CommandError

ROOT = Path(__file__).resolve().parents[3]


def test_procfile_starts_gunicorn_without_an_access_log_and_migrates_after_deploy():
    procfile = (ROOT / "Procfile").read_text()
    assert "web: gunicorn config.wsgi" in procfile
    assert "$PORT" in procfile
    # The roadmap token is in the URL: gunicorn must not log requests (docs/guides/06).
    assert "access" not in procfile
    assert "postdeploy:" in procfile


@pytest.mark.parametrize("script", ["bin/post_compile", "bin/post_deploy.sh"])
def test_hook_scripts_are_executable(script):
    assert os.stat(ROOT / script).st_mode & stat.S_IXUSR


def test_the_build_compiles_tailwind_before_collecting_static_files():
    steps = (ROOT / "bin/post_compile").read_text()
    assert steps.index("tailwind build") < steps.index("collectstatic")


def test_the_deploy_hook_migrates_and_sets_the_site_domain():
    hook = (ROOT / "bin/post_deploy.sh").read_text()
    assert "manage.py migrate" in hook and "set_site_domain" in hook


def test_cron_purges_deleted_tenants_every_day():
    jobs = json.loads((ROOT / "cron.json").read_text())["jobs"]
    assert any("purge_deleted_tenants" in job["command"] for job in jobs)


def test_the_build_installs_the_pdf_libraries_and_the_pinned_python():
    assert "apt-buildpack" in (ROOT / ".buildpacks").read_text()
    assert "libpango-1.0-0" in (ROOT / "Aptfile").read_text()
    assert (ROOT / ".python-version").read_text().strip() == "3.12"
    assert "requirements/prod.txt" in (ROOT / "requirements.txt").read_text()


@pytest.mark.django_db
def test_set_site_domain_updates_the_site(settings):
    settings.SITE_DOMAIN = "bord-pro.fr"

    call_command("set_site_domain")

    assert Site.objects.get(pk=settings.SITE_ID).domain == "bord-pro.fr"


@pytest.mark.django_db
def test_set_site_domain_needs_a_domain(settings):
    settings.SITE_DOMAIN = ""
    with pytest.raises(CommandError):
        call_command("set_site_domain")


def _package_names(path):
    """Package names written in a requirements file (extras and versions left out)."""
    names = set()
    for line in path.read_text().splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        names.add(re.split(r"[\[<>=!~; ]", line, maxsplit=1)[0].lower().replace("_", "-"))
    return names


def _pinned():
    pins = {}
    for line in (ROOT / "requirements/constraints.txt").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            name, version = line.split("==")
            pins[name.lower().replace("_", "-")] = version
    return pins


def test_every_installed_version_is_pinned_exactly():
    base = (ROOT / "requirements/base.txt").read_text()
    assert "-c constraints.txt" in base
    for line in (ROOT / "requirements/constraints.txt").read_text().splitlines():
        assert line.startswith("#") or re.fullmatch(r"[A-Za-z0-9._-]+==[A-Za-z0-9.!+_-]+", line), (
            line
        )


@pytest.mark.parametrize("name", ["base", "dev", "prod"])
def test_every_package_we_ask_for_has_a_pinned_version(name):
    pins = _pinned()
    missing = _package_names(ROOT / f"requirements/{name}.txt") - set(pins)
    assert not missing, f"not pinned in requirements/constraints.txt: {sorted(missing)}"


def test_django_stays_on_the_52_lts():
    assert _pinned()["django"].startswith("5.2.")


def test_dependabot_and_the_audit_are_configured():
    assert "package-ecosystem: pip" in (ROOT / ".github/dependabot.yml").read_text()
    assert "pip-audit" in (ROOT / ".github/workflows/ci.yml").read_text()
    assert "pip-audit" in (ROOT / "requirements/dev.txt").read_text()
