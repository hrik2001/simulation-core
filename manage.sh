#!/bin/bash
# Wrapper around docker's manage.py
docker-compose exec web python manage.py $@
