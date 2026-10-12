#!/bin/bash
# Runs in a one-off container after each successful build, before the new version goes live.
set -euo pipefail
python manage.py migrate --noinput
python manage.py set_site_domain
