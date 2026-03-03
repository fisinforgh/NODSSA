@echo off
REM Script para ejecutar el Comparador de Ozono en Windows

echo ========================================
echo    Comparador de Ozono - UDISTRITAL
echo ========================================

REM Verificar si existe el entorno virtual
if not exist ".venv" (
    echo Creando entorno virtual...
    python -m venv .venv
)

REM Activar entorno virtual
echo Activando entorno virtual...
call .venv\Scripts\activate.bat

REM Verificar si están instaladas las dependencias
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias...
    pip install -r requirements.txt
)

REM Ejecutar la aplicación
echo Iniciando aplicacion...
python -m app.main

REM Pausar para ver cualquier mensaje de error
pause
