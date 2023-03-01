#!/bin/bash

clear
clear

autopep8 -i *.py --max-line-length 200
#pylint --max-line-length=200 main.py

./main.py
