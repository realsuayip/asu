files_env := env("ASU_COMPOSE_FILES", "compose.yml workers.yml")
files_abs := prepend("docker/dev/", files_env)
files := prepend("-f ", files_abs)
service := "asu-web"

_default: (docker 'up -d')

# Run a docker-compose command
docker *args:
    docker compose {{ files }} {{ args }}

# Build Docker containers
build *args: (docker 'build' args)

# Start docker containers and attach to them
up *args: (docker 'up' args)

# Stop all Docker containers
stop *args: (docker 'stop' args)

# Run a shell command in Django container
exec *args:
    docker exec -it {{ service }} {{ args }}

# Enter Django container console
console *args: (exec '/bin/sh' args)

# Check type hints
type: (exec 'mypy asu/')

# Expose uv interface
uv *args: (exec 'uv' args)

# Create or update translation files
makemessages: (exec '/bin/sh -c "./manage.py makemessages --all --no-obsolete"')

# Compile translation files
compilemessages: (exec '/bin/sh -c "./manage.py compilemessages --ignore .venv"')

# Compile documentation
docs:
    make -C docs clean html

# Run pre-commit
format *args:
    pre-commit run {{ args }}

# Follow logs for given container.
logs container=service:
    docker logs {{ container }} --tail 500 --follow

# Execute a Django management command
run *args:
    docker exec -it {{ service }} python manage.py {{ args }}

# Enter Django shell
shell: (run 'shell')

# Run tests
test *args: (exec 'pytest --reuse-db --no-migrations' args)

alias mypy := type
alias f := format
alias t := test
alias l := logs
