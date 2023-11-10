@echo off
set FLASK_APP=./movies/index.py
pipenv run flask run --debug -h 0.0.0.0