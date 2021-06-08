DOCKER_TAG			?= qrater:development
PULL						?= false
NO_CACHE				?= false
BUILD_TYPE			?= development
CONTAINER_NAME	?= qrater
CLIENT_PORT		 ?= 8000
DOCKER_REPO		 ?= <URL to docker repo>
HOST						?= $(shell hostname)

SECRET_KEY			?=
MAIL_SERVER		 ?=
MAIL_PORT			 ?=
MAIL_USE_TLS		?=
MAIL_USERNAME	 ?=
# MAIL_PASSWORD	 ?= <FOR SECURITY DON'T PUT HERE>



.DEFAULT_GOAL := help

build:
	# Build the dockerfile
	docker build --pull=${PULL} --no-cache=${NO_CACHE} -t ${DOCKER_TAG} .

create:
	# Create the container
	echo 'Creating container in ${HOST} accessible at port: ${CLIENT_PORT}'
	docker create \
		--name ${CONTAINER_NAME}_${BUILD_TYPE} \
		-p ${CLIENT_PORT}:5000 \
		${DOCKER_TAG}

start:
	echo 'Running container in ${HOST} accessible at port: ${CLIENT_PORT}'
	docker start ${CONTAINER_NAME}_${BUILD_TYPE}

run:
	# Create and start the container
	make create -e \
		HOST=$(shell hostname) \
		CLIENT_PORT=${CLIENT_PORT} \
		CONTAINER_NAME=${CONTAINER_NAME} \
		BUILD_TYPE=${BUILD_TYPE} \
		DOCKER_TAG=${DOCKER_TAG}
	make start -e BUILD_TYPE=${BUILD_TYPE}
	make show

stop:
	# Stop a running container
	docker stop ${CONTAINER_NAME}_${BUILD_TYPE}

clean_container:
	# Remove previous container
	docker rm -f ${CONTAINER_NAME}_${BUILD_TYPE} 2>/dev/null \
		&& echo 'Container for "${CONTAINER_NAME}_${BUILD_TYPE}" removed.' \
		|| echo 'Container for "${CONTAINER_NAME}_${BUILD_TYPE}"' \
			'already removed or not found.'

clean_image:
	# Remove created image
	docker rmi ${DOCKER_TAG} 2>/dev/null \
		&& echo 'Image(s) for "${DOCKER_TAG}" removed.' \
		|| echo 'Image(s) for "${DOCKER_TAG}" already removed or not found.'

show:
	# Show running containers
	docker ps | grep ${CONTAINER_NAME}

rebuild:
	# Rebuild the dockerfile
	make clean_container -e BUILD_TYPE=${BUILD_TYPE}
	make build -e PULL=true NO_CACHE=true DOCKER_TAG=${DOCKER_TAG}

up:
	# Run container on port
	make build -e PULL=true NO_CACHE=true DOCKER_TAG=${DOCKER_TAG}
	make run -e CLIENT_PORT=${CLIENT_PORT} BUILD_TYPE=${BUILD_TYPE} \
		DOCKER_TAG=${DOCKER_TAG}

#login:
	## Run as a service and attach to it
	#docker exec -it ${CONTAINER_NAME}_${BUILD_TYPE} flask shell

#release:
	#make build -e PULL=true NO_CACHE=true DOCKER_TAG=${DOCKER_TAG}
	#make push -e VERSION=${VERSION}

#push:
	#docker push ${DOCKER_REPO}/${CONTAINER_NAME}:${VERSION}

#pull:
	#docker pull ${DOCKER_REPO}/${CONTAINER_NAME}:${VERSION}

# Docker tagging
tag:
	@echo 'create tag ${VERSION}'
	docker tag ${DOCKER_TAG} ${DOCKER_REPO}/${CONTAINER_NAME}:${VERSION}

help:
	@echo ''
	@echo 'Usage: make [TARGET] [EXTRA_ARGUMENTS]'
	@echo 'Targets:'
	@echo '  build            build docker --image--'
	@echo '  rebuild          rebuild docker --image--'
	@echo '  login            run as service and login --container--'
	@echo '  clean_image      remove docker --image-- '
	@echo ''
	@echo 'Extra arguments:'
	@echo 'CONTAINER_NAME=:   make clean_container -e CONTAINER_NAME=my_app' \
		'(no need to provide this param, it will be set by default)'
	@echo 'BUILD_TYPE=:       make clean_container -e CONTAINER_NAME=my_app' \
		'BUILD_TYPE=staging'
	@echo 'DOCKER_TAG=:       make build -e DOCKER_TAG=my_app:staging'
	@echo 'CLIENT_PORT=:      make create -e CLIENT_PORT=8000'
