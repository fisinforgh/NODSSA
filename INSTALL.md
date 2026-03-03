# Instalación y ejecución — NODSSA

Esta guía resume la instalación recomendada basada en el Manual Técnico. El enfoque principal es Linux (Ubuntu 20.04 LTS o superior). Windows y macOS también son compatibles mediante entornos virtuales de Python.

## 1) Linux (Ubuntu 20.04+)

### Paso 1 — Dependencias del sistema
```bash
sudo apt-get update
sudo apt-get install build-essential python3-dev python3-venv
```

### Paso 2 — Entorno virtual
Desde la raíz del repositorio o desde tu carpeta de trabajo:

```bash
python3 -m venv venv_ozono
source venv_ozono/bin/activate
```

### Paso 3 — Descargar el código
```bash
git clone https://github.com/fisinforgh/NODSSA.git
cd NODSSA
```

### Paso 4 — Instalar dependencias Python
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 5 — Ejecutar la GUI
```bash
python GUI/ComparadorOzono/app/main.py
```

Si tu despliegue requiere rutas específicas de datos, revisa los archivos de constantes (por ejemplo `constantes.py`) y ajusta según tu estructura local.

## 2) Windows

### Opción A — con venv (PowerShell)
```powershell
py -3.12 -m venv venv_ozono
.\venv_ozono\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
python GUI\ComparadorOzono\app\main.py
```

### Opción B — con conda
```powershell
conda create -n solar_ozone python=3.12 -y
conda activate solar_ozone
python -m pip install -U pip
pip install -r requirements.txt
python GUI\ComparadorOzono\app\main.py
```

## 3) macOS

```bash
python3 -m venv venv_ozono
source venv_ozono/bin/activate
pip install -U pip
pip install -r requirements.txt
python GUI/ComparadorOzono/app/main.py
```

## 4) Empaquetar la GUI como ejecutable (PyInstaller)

Nota: se debe generar un build por sistema operativo (Linux construye binario Linux; Windows construye .exe).

### Linux (desde la carpeta `GUI/` si existe `ComparadorOzono/` dentro)
```bash
cd GUI
rm -rf build dist *.spec

python -m PyInstaller --noconfirm --clean --windowed   --name NODSSA   --collect-all PySide6   --add-data "ComparadorOzono/app/assets:ComparadorOzono/app/assets"   --add-data "ComparadorOzono/app/styles:ComparadorOzono/app/styles"   ComparadorOzono/app/main.py
```

Ejecutar:
```bash
./dist/NODSSA/NODSSA
```

Empaquetar para distribuir:
```bash
tar -czf NODSSA_linux_x86_64.tar.gz -C dist NODSSA
```

### Windows (PowerShell; el separador de --add-data es ';')
```powershell
cd GUI
Remove-Item -Recurse -Force build,dist,*.spec -ErrorAction SilentlyContinue

python -m PyInstaller --noconfirm --clean --windowed `
  --name NODSSA `
  --collect-all PySide6 `
  --add-data "ComparadorOzono\app\assets;ComparadorOzono\app\assets" `
  --add-data "ComparadorOzono\app\styles;ComparadorOzono\app\styles" `
  ComparadorOzono\app\main.py
```

## 5) Troubleshooting rápido

- Si aparece `ModuleNotFoundError: No module named 'PySide6'`, confirma que PySide6 está instalado en el mismo entorno donde estás ejecutando PyInstaller y construye con `python -m PyInstaller` (evita mezclar entornos).
- Si faltan íconos/temas en el ejecutable, revisa que `assets/` y `styles/` estén incluidos con `--add-data` y que el ResourceManager resuelva rutas en modo “frozen”.
