FROM python:3.11-bullseye
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends netcat
RUN python -m pip install pip-tools~=6.12

WORKDIR /code

ADD ./requirements.txt /code/requirements.txt
RUN pip-sync requirements.txt --pip-args "--no-cache-dir --no-deps"

COPY . /code
ENTRYPOINT ["/code/docker/scripts/entrypoint.sh"]
