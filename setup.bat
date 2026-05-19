@echo off
title Notion Engine - Instalador
echo ====================================
echo   Notion Engine - Instalacion
echo ====================================
echo.

if not exist "venv" (
    echo [1/3] Creando entorno virtual...
    python -m venv venv
) else (
    echo [1/3] Entorno virtual ya existe.
)

echo [2/3] Instalando dependencias...
call venv\Scripts\activate
pip install -r requirements.txt > nul
echo Completado.

if not exist ".env" (
    echo [3/3] Creando archivo .env...
    copy .env.example .env > nul
    echo.
    echo ====================================
    echo   IMPORTANTE!
    echo ====================================
    echo Abri el archivo .env con el bloc de notas
    echo y completa estos datos:
    echo.
    echo 1. Crea una integracion en:
    echo    https://www.notion.so/my-integrations
    echo    Pega el token en NOTION_TOKEN
    echo.
    echo 2. Crea una API Key gratis en:
    echo    https://console.groq.com/keys
    echo    Pega la key en OPENAI_API_KEY
    echo.
    echo 3. Abri tu pagina de Notion y copia el ID
    echo    de la URL en NOTION_PAGE_ID
    echo.
    pause
) else (
    echo [3/3] Archivo .env ya existe.
)

echo.
echo ====================================
echo   Instalacion completada!
echo ====================================
echo.
echo Para iniciar la app hace doble clic en:
echo   INICIAR.bat
echo.
echo Despues abri http://127.0.0.1:8000
echo.
pause
