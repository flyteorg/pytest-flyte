PIP_COMPILE = pip-compile --upgrade --verbose

.PHONY: install-piptools
install-piptools:
	pip install -U pip-tools

requirements.txt: export CUSTOM_COMPILE_COMMAND := make requirements.txt
requirements.txt: requirements.in install-piptools
	$(PIP_COMPILE) $<

dev-requirements.txt: export CUSTOM_COMPILE_COMMAND := make dev-requirements.txt
dev-requirements.txt: dev-requirements.in requirements.txt install-piptools
	$(PIP_COMPILE) $<

.PHONY: requirements
requirements: requirements.txt dev-requirements.txt

.PHONY: setup
setup: install-piptools ## Install requirements
	pip-sync requirements.txt dev-requirements.txt
