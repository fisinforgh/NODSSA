#!/bin/bash
# Script para ejecutar el Comparador de Ozono

# Colores para mensajes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Comparador de Ozono - UDISTRITAL${NC}"
echo -e "${GREEN}========================================${NC}"

# Verificar si existe el entorno virtual
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creando entorno virtual...${NC}"
    python3 -m venv .venv
fi

# Activar entorno virtual
echo -e "${YELLOW}Activando entorno virtual...${NC}"
source .venv/bin/activate

# Verificar si están instaladas las dependencias
if ! python -c "import PySide6" &> /dev/null; then
    echo -e "${YELLOW}Instalando dependencias...${NC}"
    pip install -r requirements.txt
fi

# Ejecutar la aplicación
echo -e "${GREEN}Iniciando aplicación...${NC}"
python -m app.main

# Desactivar entorno virtual al salir
deactivate
