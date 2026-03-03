Comparador de Ozono - Real vs Predicho
 Descripción
Aplicación de escritorio desarrollada en Python para comparar datos reales y predichos de concentraciones de ozono. Realiza análisis estadísticos exhaustivos y genera visualizaciones diagnósticas para evaluar la calidad de los modelos predictivos.
 Características principales

Análisis estadístico completo: Chi², Shapiro-Wilk, Breusch-Pagan, Durbin-Watson, Ljung-Box
Visualizaciones diagnósticas: Histogramas, Q-Q plots, ACF, scatter plots
Interfaz moderna: Tema claro/oscuro, diseño responsivo
Exportación de resultados: Gráficos en PNG y reportes detallados

 Requisitos

Python 3.12 o superior
Sistema operativo: Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+)
Mínimo 4GB RAM
100MB espacio en disco

 Instalación
1. Clonar o descargar el proyecto
bashgit clone https://github.com/tu-usuario/comparador-ozono.git
cd ComparadorOzono
2. Crear entorno virtual
bash# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
3. Instalar dependencias
bashpip install -r requirements.txt
🚀 Ejecución
Modo desarrollo
bashpython -m app.main
Crear ejecutable
bash# Windows
pyinstaller --noconfirm --clean --windowed --onefile --add-data "app/assets;assets" --add-data "app/styles;styles" --name "ComparadorOzono" app/main.py

# macOS/Linux
pyinstaller --noconfirm --clean --windowed --onefile --add-data "app/assets:assets" --add-data "app/styles:styles" --name "ComparadorOzono" app/main.py
📖 Uso

Iniciar la aplicación: Ejecutar el comando o doble clic en el ejecutable
Cargar datos:

Click en "Cargar ozono REAL" → Seleccionar archivo CSV
Click en "Cargar ozono PREDICHO" → Seleccionar archivo CSV


Ejecutar análisis: Click en "Ejecutar diagnósticos"
Revisar resultados:

Tabla con pruebas estadísticas
Gráficos guardados en carpeta out_plots/



Formato de archivos CSV
Los archivos deben contener las siguientes columnas:

Date: Fecha en formato YYYY-MM-DD
Ozone: Valor de concentración de ozono (numérico)

 Pruebas estadísticas
PruebaDescripciónCriterio de éxitoChi² GlobalBondad de ajustep-valor ≥ 0.05Shapiro-WilkNormalidadp-valor ≥ 0.05Breusch-PaganHomocedasticidadp-valor ≥ 0.05Durbin-WatsonAutocorrelación AR(1)1.5 ≤ DW ≤ 2.5Ljung-BoxAutocorrelación generalp-valor ≥ 0.05
 Tests
bashpytest tests/ -v --cov=app
 Estructura del proyecto
ComparadorOzono/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Punto de entrada
│   ├── core/                   # Lógica central
│   │   ├── __init__.py
│   │   ├── constantes.py       # Configuración global
│   │   ├── diagnosticos.py     # Análisis estadístico
│   │   ├── recursos.py         # Gestión de rutas
│   │   └── tema.py            # Gestión de temas
│   ├── ui/                    # Interfaz de usuario
│   │   ├── __init__.py
│   │   ├── splash_window.py   # Pantalla de inicio
│   │   ├── main_window.py     # Ventana principal
│   │   └── dialog_about.py    # Diálogo Acerca de
│   ├── viewmodels/            # Lógica de presentación
│   │   ├── __init__.py
│   │   └── analisis_vm.py     # ViewModel del análisis
│   ├── assets/                # Recursos gráficos
│   │   └── logo_universidad.png
│   └── styles/                # Estilos
│       ├── theme_dark.qss
│       └── theme_light.qss
├── tests/                     # Pruebas unitarias
├── requirements.txt           # Dependencias
└── README.md                 # Documentación
 Autores

Universidad Distrital Francisco Jose de Caldas 
Facultad de Ingeneria
Maestria de Ciencias de la Informacion 

 Licencia
MIT License - Ver archivo LICENSE para más detalles
 Contribuciones
Las contribuciones son bienvenidas. Por favor, abra un issue primero para discutir los cambios propuestos.


Versión: 1.0.0
Última actualización: Septiembre 2025
