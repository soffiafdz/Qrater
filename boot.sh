#!/bin/sh
source env/bin/activate
flask db upgrade
exec gunicorn -b :5000 --access-logfile - --error-logfile - qrater:app
