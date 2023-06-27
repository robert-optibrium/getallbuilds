@echo off
if not exist .\venv (
	echo Creating VENV
	python -m venv venv
)
call venv\scripts\activate
if not exist .\venv\Lib\site-packages\urllib3 (
	pip install -r requirements.txt
)
if %1x == "x" then (
:loop
python main.py -gab -usr ci-admin -tok 11781cc9c3f25ba91eb220281edcd10ec1 
timeout /t 2400
echo ========================================
goto loop
) else (
exit /b 
)
call deactivate