@echo off
title Notion Engine
echo ====================================
echo   Iniciando Notion Engine...
echo ====================================
echo.
echo Abri en tu navegador: http://127.0.0.1:8000
echo.

call venv\Scripts\activate
python manage.py runserver

pause
