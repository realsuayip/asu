FROM python:3.10.1
ENV PYTHONUNBUFFERED 1

RUN mkdir /code
WORKDIR /code
COPY . /code

RUN apt-get update && apt-get install -y netcat
RUN pip install -r requirements.txt

ENTRYPOINT ["/code/docker/scripts/entrypoint.sh"]
