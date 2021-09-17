#!/bin/sh

CONTAINER="qrater_db_1"
BACKUP_DIR="/data/ipl/scratch22/sfernandez/backup_sql_qrater"

docker run \
	--rm \
	--volumes-from $CONTAINER \
	-v $BACKUP_DIR:/backup \
	ubuntu bash \
	-c "cd /var/lib/mysql && tar cvf /backup/sql_$(date +%Y%m%d).tar ."
