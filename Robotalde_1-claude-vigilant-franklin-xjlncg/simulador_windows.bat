@echo off
rem LeWelder - simulador de la demo en Windows (doble clic).
rem La primera vez crea el entorno .venv-sim e instala las dependencias ligeras (sin PyTorch ni LeRobot, ~150 MB).
rem Despues arranca el simulador y abre http://localhost:8080/ en el navegador.
setlocal
cd /d "%~dp0"
title LeWelder - simulador

rem Python 3.12 a usar: el que digas en LEWELDER_PYTHON, o "py -3.12", o el "python" del PATH si es 3.12.
rem Ejemplo: set LEWELDER_PYTHON=D:\ruta\a\python.exe  y luego  simulador_windows.bat
if exist ".venv-sim\Scripts\python.exe" goto arrancar
set "PYEXE="
if defined LEWELDER_PYTHON set "PYEXE="%LEWELDER_PYTHON%""
if not defined PYEXE (
    py -3.12 -c "import sys" >nul 2>nul && set "PYEXE=py -3.12"
)
if not defined PYEXE (
    python -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>nul && set "PYEXE=python"
)
if not defined PYEXE goto sin_python
%PYEXE% -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>nul
if errorlevel 1 goto sin_python

if not exist ".venv-sim\Scripts\python.exe" (
    echo [LeWelder] Primera vez: creando el entorno .venv-sim con %PYEXE% ...
    %PYEXE% -m venv .venv-sim || goto error
    ".venv-sim\Scripts\python.exe" -m pip install --upgrade pip || goto error
    ".venv-sim\Scripts\python.exe" -m pip install -r herramientas\space\requirements-space.txt || goto error
    echo [LeWelder] Instalado.
)

:arrancar
set PYTHONPATH=%~dp0
set PYTHONUNBUFFERED=1
set MUJOCO_GL=disable
echo [LeWelder] Arrancando el simulador. Para pararlo, cierra esta ventana o pulsa Ctrl+C.
echo [LeWelder] Se abrira http://localhost:8080/ (si no, abrelo a mano en Chrome o Edge).
start "" cmd /c "timeout /t 8 >nul && start http://localhost:8080/"
".venv-sim\Scripts\python.exe" -m lewelder.simulador --host 127.0.0.1 --puerto 8080
goto fin

:sin_python
echo.
echo [LeWelder] Falta Python 3.12. Instalalo con:
echo     winget install Python.Python.3.12
echo o desde https://www.python.org/downloads/ (marca "Add python.exe to PATH" y el lanzador "py").
echo Despues vuelve a hacer doble clic en este archivo.
pause
goto fin

:error
echo.
echo [LeWelder] Algo ha fallado en la instalacion. Copia el texto de arriba y pasaselo a Claude.
pause

:fin
endlocal
