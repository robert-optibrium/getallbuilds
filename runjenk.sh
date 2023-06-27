#!/bin/bash
if not exist ./venv (
	echo Creating VENV
	python -m venv venv
	source venv/bin/activate
	pip install -r requirements.txt
) else (
	source venv/bin/activate
)
python main.py -gab -gpd -nod -geb -usr robert@optibrium.com -tok 11bf54d1a2a09cf5c2b52971ec0d848568
call deactivate