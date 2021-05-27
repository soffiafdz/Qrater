#!/bin/sh
source env/bin/activate
flask db upgrade
exec gunicorn -b :8080 --access-logfile - --error-logfile - qrater:app
