FROM python:3.6-alpine

RUN adduser -D admin

WORKDIR /home/qrater

COPY requirements.txt requirements.txt
RUN python -v venv env
RUN env/bin/pip install -r requirements.txt

COPY app app
COPY migrations migrations
COPY qrater.py config.py boot.sh ./
RUN chmod +x boot.sh

ENV FLASK_APP qrater.py

RUN chown -R admin:qrater ./
USER admin

EXPOSE 8080
ENTRYPOINT ["./boot.sh"]
