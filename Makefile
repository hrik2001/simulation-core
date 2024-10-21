.PHONY: help install-dev lint format test run migrate makemigrations shell clean

help:
	@echo "Available commands:"
	@echo "  make install-dev    : Install development dependencies"
	@echo "  make lint           : Run linters (flake8, mypy)"
	@echo "  make format         : Format code (black, isort)"
	@echo "  make test           : Run tests"
	@echo "  make run            : Run Django development server"
	@echo "  make migrate        : Run Django migrations"
	@echo "  make makemigrations : Make Django migrations"
	@echo "  make shell          : Open Django shell"
	@echo "  make clean          : Remove Python file artifacts"
	@echo "  make precommit      : Run pre-commit on all files"

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

lint:
	flake8 .
	mypy .

format:
	black .
	isort .

test:
	python manage.py test

run:
	python manage.py runserver

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

shell:
	python manage.py shell

clean:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

precommit:
	pre-commit run --all-files
