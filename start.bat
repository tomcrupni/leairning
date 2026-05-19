@echo off
title LeAIrning - Servidor
color 0A
echo.
echo  ██╗     ███████╗ █████╗ ██╗██████╗ ███╗   ██╗██╗███╗   ██╗ ██████╗
echo  ██║     ██╔════╝██╔══██╗██║██╔══██╗████╗  ██║██║████╗  ██║██╔════╝
echo  ██║     █████╗  ███████║██║██████╔╝██╔██╗ ██║██║██╔██╗ ██║██║  ███╗
echo  ██║     ██╔══╝  ██╔══██║██║██╔══██╗██║╚██╗██║██║██║╚██╗██║██║   ██║
echo  ███████╗███████╗██║  ██║██║██║  ██║██║ ╚████║██║██║ ╚████║╚██████╔╝
echo  ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═══╝ ╚═════╝
echo.
echo  Iniciando servidor...
echo.

cd /d "%~dp0"

echo  [1/2] Instalando dependencias...
set PYTHON=C:\Users\Windows\AppData\Local\Programs\Python\Python313\python.exe
if not exist "%PYTHON%" set PYTHON=py
if not exist "%PYTHON%" set PYTHON=python

"%PYTHON%" -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo  ERROR: No se pudo instalar dependencias. Verifica que Python este instalado.
    pause
    exit /b 1
)

echo  [2/2] Arrancando servidor LOCAL en http://localhost:8000
echo.
echo  Local:  http://localhost:8000
echo  Online: https://leairning.onrender.com
echo.
echo  Presiona Ctrl+C para detener el servidor local.
echo.

"%PYTHON%" main.py

pause
