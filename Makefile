SHELL := /bin/bash
ifeq ($(OS),Windows_NT)
    PYTHON = python.exe
    ACTIVATE_VENV = venv\Scripts\activate
else
    PYTHON = python3.11
    ACTIVATE_VENV = source venv/bin/activate
endif
PIP = $(PYTHON) -m pip

.PHONY: env init pre-commit requirements lint clean force-release help

# Default target executed when no arguments are given to make.
all: help

env:
	ifneq ("$(wildcard .env)","")
		include .env
	else
		$(shell echo -e "AWS_REGION=us-east-2" >> .env)
		$(shell echo -e "DEBUG_MODE=False" >> .env)
	endif

# -------------------------------------------------------------------------
# Initialize. create virtual environment and install requirements
# -------------------------------------------------------------------------
init:
	make clean && \
	$(PYTHON) -m venv venv && \
	$(ACTIVATE_VENV) && \
	$(PIP) install --upgrade pip && \
	make requirements

# -------------------------------------------------------------------------
# Install requirements: Python, npm and pre-commit
# -------------------------------------------------------------------------
requirements:
	rm -rf .tox && \
	$(PIP) install --upgrade pip wheel && \
	$(PIP) install -r requirements/dev.txt && \
	npm install && \
	pre-commit install && \
	pre-commit autoupdate && \
	pre-commit run --all-files

# -------------------------------------------------------------------------
# Run black and pre-commit hooks.
# includes prettier, isort, flake8, pylint, etc.
# -------------------------------------------------------------------------
lint:
	pre-commit run --all-files && \
	pylint ./swpwrxblock/ && \
	flake8 . && \
	isort . && \
	black ./swpwrxblock/ && \
	black --line-length 120 swpwrxblock/swpwrxblock.py && \
	docformatter --in-place --wrap-summaries 120 --wrap-descriptions 120 swpwrxblock/swpwrxblock.py

# -------------------------------------------------------------------------
# Destroy all build artifacts and Python temporary files
# -------------------------------------------------------------------------
clean:
	@rm -rf .pytest_cache
	@rm -rf .mypy_cache
	@rm -rf build
	@rm -rf dist
	@rm -rf swpwrxblock.egg-info
	@test -d swpwrxblock/public/dist && rm -rf swpwrxblock/public/dist || true



build:
	make clean && \
	pip cache purge && \
	pip wheel . -v -w dist

# -------------------------------------------------------------------------
# Run Python unit tests
# -------------------------------------------------------------------------

# -------------------------------------------------------------------------
# Force a new semantic release to be created in GitHub
# -------------------------------------------------------------------------
force-release:
	git commit -m "fix: force a new release" --allow-empty && git push

update:
	npm install -g npm && \
	npm install -g npm-check-updates && \
	ncu --upgrade --packageFile ./package.json && \
	npm update -g && \
	make init


# -------------------------------------------------------------------------
# Generate help menu
# -------------------------------------------------------------------------
help:
	@echo '===================================================================='
	@echo 'init			- build virtual environment and install requirements'
	@echo 'requirements		- install Python, npm and pre-commit requirements'
	@echo 'lint			- run black and pre-commit hooks'
	@echo 'force-release		- force a new release to be created in GitHub'
