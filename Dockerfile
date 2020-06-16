FROM python:3.8-slim-buster

LABEL authors="Christoph Kiss, Matthias Weiß"

WORKDIR /

COPY ./Sport-sessions /Sport-sessions
COPY requirements.txt /
COPY migrate.py /

RUN pip3 install -r ./requirements.txt

# -u enables unbuffered binary stdout and stderr, otherwise print did not work
ENTRYPOINT ["python3", "-u", "./migrate.py"]
