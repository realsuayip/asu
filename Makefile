WHATEVER := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
$(eval $(WHATEVER):;@:)
# ^ Captures all the stuff passed after the target. If you are going
# to pass options, you may do so by using "--" e.g.:
# make up -- --build

file = docker/docker-compose.yml
ifeq (${CONTEXT}, production)
	file = docker/docker-compose.prod.yml
endif

project = asu
cc = docker compose -p $(project) -f $(file)
ex = docker exec -it asu-web
dj = $(ex) python manage.py

.PHONY: *
.DEFAULT_GOAL := detach

build:
	$(cc) build $(WHATEVER)
up:
	$(cc) up $(WHATEVER)
detach:
	$(cc) up -d $(WHATEVER)
ifneq (${CONTEXT}, production)
down:
	$(cc) down $(WHATEVER)
endif
stop:
	$(cc) stop $(WHATEVER)
compose:
	$(cc) $(WHATEVER)
logs:
	docker logs $(WHATEVER) --tail 500 --follow
console:
	$(ex) /bin/bash
run:
	$(dj) $(WHATEVER)
shell:
	$(dj) shell
test:
	$(dj) test --settings=asu.settings.test --parallel 4 --shuffle --timing --keepdb
coverage:
	$(ex) /bin/sh -c "coverage run ./manage.py test --shuffle --settings=asu.settings.test --no-input &&\
 					  coverage html --omit='*/test_*.py,*/tests.py,*/migrations/*' --skip-empty"
	open htmlcov/index.html
format:
	pre-commit run
type:
	$(ex) /bin/sh -c "MYPY_FORCE_COLOR=true mypy asu/ |\
					   grep -v 'Metaclass conflict\|Import cycle\|AnonymousUser\|Constraint'"
