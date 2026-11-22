@echo off
rem Visor 3D de Garbi en Windows: trae lo último de GitHub y abre el visor de MuJoCo.
rem Requisitos: Git y Python 3.10-3.13 (https://www.python.org, marcar "Add python.exe to PATH" al instalar).
setlocal
cd /d "%~dp0\.."
set RAMA=claude/vigilant-franklin-xjlncg

echo === Trayendo lo ultimo de GitHub (%RAMA%) ===
git fetch origin %RAMA% || goto :error
git checkout %RAMA% || goto :error
git pull --ff-only origin %RAMA% || goto :error

if not exist .venv-visor\Scripts\python.exe (
    echo === Primera vez: creando el entorno del visor ===
    rem Cualquier Python 3.10-3.13 vale para el visor
    py -3.12 -m venv .venv-visor 2>nul || py -3.13 -m venv .venv-visor 2>nul || py -3.11 -m venv .venv-visor 2>nul || py -3.10 -m venv .venv-visor 2>nul || python -m venv .venv-visor || goto :sinpython
    .venv-visor\Scripts\python -m pip install --upgrade pip
    .venv-visor\Scripts\python -m pip install mujoco numpy opencv-python pillow || goto :error
)

echo === Abriendo el visor ===
.venv-visor\Scripts\python -m garbi.ver
goto :eof

:sinpython
echo.
echo No encuentro Python 3.10-3.13. Instalalo desde https://www.python.org/downloads/ marcando
echo "Add python.exe to PATH", cierra esta ventana, abre otra y vuelve a ejecutar este archivo.
pause
goto :eof

:error
echo.
echo Algo ha fallado. Copia el mensaje de arriba y pasamelo.
pause
