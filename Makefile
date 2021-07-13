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

PLACEHOLDER := "__version__\ =\ \"0.0.0+develop\""

.PHONY: update-version
update-version:
	# ensure the placeholder is there. If grep doesn't find the placeholder
	# it exits with exit code 1 and github actions aborts the build.
	grep "$(PLACEHOLDER)" "src/pytest_flyte/__init__.py"
	sed -i "s/$(PLACEHOLDER)/__version__ = \"${VERSION}\"/g" "src/pytest_flyte/__init__.py"

	grep "$(PLACEHOLDER)" "setup.py"
	sed -i "s/$(PLACEHOLDER)/__version__ = \"${VERSION}\"/g" "setup.py"
