#!/usr/bin/env python
import os
import sys
import django
from django.core.management import execute_from_command_line

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lumber.settings")
django.setup()

execute_from_command_line(["manage.py", "makemigrations", "app_round_wood"])
