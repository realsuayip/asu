env := env("ASU_DOCKER_ENV", "dev")
file := "docker/" + env + "/docker-compose.yml"

_default: (docker 'up -d')

# Run a docker-compose command
docker *args:
    docker compose -p asu -f {{ file }} {{ args }}

# Build Docker containers
build *args: (docker 'build' args)

# Start docker containers and attach to them
up *args: (docker 'up' args)

# Remove all Docker containers
down *args: (docker 'down' args)

# Stop all Docker containers
stop *args: (docker 'stop' args)

# Run a shell command in Django container
exec *args:
    docker exec -it asu-web {{ args }}

# Enter Django container console
console *args: (exec '/bin/sh' args)

# Run tests with coverage
coverage: (exec '/bin/sh -c \
    "coverage run --concurrency=multiprocessing \
    ./manage.py test \
    --parallel 4 \
    --shuffle \
    --timing \
    --settings=asu.settings.test \
    --no-input && \
    coverage combine && \
    coverage html"')

# Check type hints
type: (exec 'mypy asu/ --no-incremental')

# Create or update translation files
makemessages: (exec '/bin/sh -c "cd asu && ../manage.py makemessages --all --no-obsolete"')

# Compile translation files
compilemessages: (exec '/bin/sh -c "cd asu && ../manage.py compilemessages"')

# Compile documentation
docs:
    make -C docs clean html

# Run pre-commit
format *args:
    pre-commit run {{ args }}

# Follow logs for given container.
logs container='asu-web':
    docker logs {{ container }} --tail 500 --follow

# Execute a Django management command
run *args:
    docker exec -it asu-web python manage.py {{ args }}

# Enter Django shell
shell: (run 'shell')

# Run tests
test: (run 'test --settings=asu.settings.test --parallel 4 --shuffle --timing --keepdb')

alias mypy := type
alias f := format
alias t := test
alias l := logs
