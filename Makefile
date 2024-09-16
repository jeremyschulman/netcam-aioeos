PACKAGE_and_VERSION = $(shell poetry version)
PACKAGE_NAME = $(word 1, $(PACKAGE_and_VERSION))
PACKAGE_VERSION = $(word 2, $(PACKAGE_and_VERSION))

precheck: code-format code-check
	pre-commit run -a && \
	interrogate -c pyproject.toml

code-format:
	ruff format --config pyproject.toml $(CODE_DIRS)

code-check:
	ruff check --config pyproject.toml $(CODE_DIRS)

clean:
	rm -rf dist *.egg-info .pytest_cache
	rm -f requirements.txt setup.py
	rm -f poetry.lock
	find . -name '__pycache__' | xargs rm -rf

doccheck:
	interrogate -vvv netinfraiac --omit-covered-files

