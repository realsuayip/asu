FROM python:3.11.1-bullseye
ENV PYTHONUNBUFFERED 1

RUN mkdir /code
WORKDIR /code
COPY . /code

RUN apt-get update && apt-get install -y --no-install-recommends netcat
RUN pip install -r requirements.txt --no-cache-dir --no-deps

ENTRYPOINT ["/code/docker/scripts/entrypoint.sh"]
