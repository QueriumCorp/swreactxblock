SHELL := /bin/bash


.PHONY: build help

# Default target executed when no arguments are given to make.
all: help



# open ./swpwrxblock/__init__.py and read the value of VERSION, 
# and bump to the next semantic patch value. Example:
#  if VERSION = "18.0.0" then the next patch would be "18.0.1"
build:
	@echo "Building..."
	@echo "Version: $(shell cat swpwrxblock/__init__.py | grep VERSION | awk '{print $$3}' | sed 's/"//g')"
	@echo "Bumping to next patch version..."
	@echo "__version__ = \"$(shell cat swpwrxblock/__init__.py | grep VERSION | awk '{print $$3}' | sed 's/"//g' | awk -F. '{print $$1"."$$2"."$$3+1}')\"" > swpwrxblock/__init__.py
	@echo "Version: $(shell cat swpwrxblock/__init__.py | grep VERSION | awk '{print $$3}' | sed 's/"//g')"
	@echo "Done!"
	
	

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build        Build the project"
	@echo "  help         Display this help message"
	@echo ""
	@echo "Default target: help"
	@echo ""