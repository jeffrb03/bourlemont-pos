@echo off
title Bourlemont Champagne Bar - POS Engine
color 0E

echo ======================================================================
echo           BOURLEMONT CHAMPAGNE BAR - CIUDAD VIEJA, SACATEPÉQUEZ
echo                  Sistema de Inventario & POS Engine
echo ======================================================================
echo.

cd /d "%~dp0\.."

REM Verificar existencia de base de datos o ejecutar sembrado
if not exist "bourlemont.db" (
    echo [INFO] Primera ejecución detectada. Inicializando base de datos...
    python scripts\init_db.py
)

REM Iniciar Uvicorn en segundo plano si no está corriendo
echo [INFO] Iniciando servidor transaccional Uvicorn en http://localhost:8000...
start /b "" python -m uvicorn main:app --host 127.0.0.1 --port 8000

REM Esperar 2 segundos para inicio del socket
timeout /t 2 /nobreak >nul

REM Lanzar navegador en modo quiosco / app sin barras de herramientas
echo [INFO] Abriendo interfaz Bourlemont en modo aplicación POS...
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --app=http://localhost:8000 --start-maximized
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --app=http://localhost:8000 --start-maximized
) else if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --app=http://localhost:8000 --start-maximized
) else (
    start http://localhost:8000
)

echo.
echo [LISTO] Sistema operando en http://localhost:8000
echo Documentación de API disponible en http://localhost:8000/docs
echo.
pause
