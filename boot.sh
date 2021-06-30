#!/bin/sh
source env/bin/activate
flask db upgrade
exec gunicorn \
	--bind :5000 \
	--timeout 90 \
	--access-logfile - \
	--error-logfile - \
	qrater:app
