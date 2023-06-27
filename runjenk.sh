#!/bin/bash
set -x
echo Creating VENV
python3 -m venv venv
ls -lr
source venv/bin/activate
pip install -r requirements.txt
python main.py -gab -gpd -nod -geb -usr robert@optibrium.com -tok 11bf54d1a2a09cf5c2b52971ec0d848568
deactivate
rm -rf venv