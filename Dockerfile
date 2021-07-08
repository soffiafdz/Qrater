FROM python:3.9-alpine

RUN adduser -D admin
RUN apk update && apk add bash python3-dev gcc g++ libc-dev

WORKDIR /home/qrater

COPY requirements.txt requirements.txt
RUN python -m venv env
RUN env/bin/pip install --upgrade pip
RUN env/bin/pip install -r requirements.txt

COPY app app
COPY migrations migrations
COPY qrater.py config.py boot.sh ./
RUN chmod +x boot.sh

ENV FLASK_APP qrater.py

RUN chown -R admin ./
USER admin

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
