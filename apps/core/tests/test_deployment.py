"""The files and commands the deployment relies on (Scalingo)."""

import json
import os
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
    # The roadmap token is in the URL: gunicorn must not log requests (docs/06).
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
