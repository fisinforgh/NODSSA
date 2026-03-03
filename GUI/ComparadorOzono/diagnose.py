#!/usr/bin/env python3
"""
Script de diagnóstico para verificar la instalación del Comparador de Ozono.
"""

import sys
import os
from pathlib import Path

def check_structure():
    """Verifica la estructura del proyecto."""
    print("\n📁 VERIFICACIÓN DE ESTRUCTURA")
    print("=" * 50)
    
    required_dirs = [
        "app",
        "app/core",
        "app/ui", 
        "app/viewmodels",
        "app/assets",
        "app/styles",
        "tests",
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ {dir_path}/")
        else:
            print(f"❌ {dir_path}/ (FALTANTE)")
            missing_dirs.append(dir_path)
    
    return len(missing_dirs) == 0

def check_files():
    """Verifica archivos críticos."""
    print("\n📄 VERIFICACIÓN DE ARCHIVOS")
    print("=" * 50)
    
    critical_files = [
        ("app/__init__.py", "Paquete app"),
        ("app/main.py", "Punto de entrada"),
        ("app/core/__init__.py", "Paquete core"),
        ("app/core/constantes.py", "Constantes"),
        ("app/core/diagnosticos.py", "Diagnósticos"),
        ("app/core/recursos.py", "Gestión de recursos"),
        ("app/core/tema.py", "Gestión de temas"),
        ("app/ui/__init__.py", "Paquete UI"),
        ("app/ui/splash_window.py", "Ventana splash"),
        ("app/ui/main_window.py", "Ventana principal"),
        ("app/ui/dialog_about.py", "Diálogo Acerca de"),
        ("app/viewmodels/__init__.py", "Paquete ViewModels"),
        ("app/viewmodels/analisis_vm.py", "ViewModel de análisis"),
        ("requirements.txt", "Dependencias"),
    ]
    
    missing_files = []
    for file_path, description in critical_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} - {description}")
        else:
            print(f"❌ {file_path} - {description} (FALTANTE)")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def check_ui_init():
    """Verifica específicamente el archivo app/ui/__init__.py."""
    print("\n🔍 VERIFICACIÓN DE app/ui/__init__.py")
    print("=" * 50)
    
    ui_init = Path("app/ui/__init__.py")
    if not ui_init.exists():
        print("❌ Archivo no encontrado")
        return False
    
    try:
        with open(ui_init, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar que NO contenga la línea problemática
        if "from .constantes import" in content:
            print("❌ Contiene importación incorrecta: 'from .constantes import *'")
            print("   Esta línea debe ser eliminada.")
            return False
        
        # Verificar imports correctos
        required_imports = [
            "from .splash_window import SplashWindow",
            "from .main_window import MainWindow",
            "from .dialog_about import DialogAbout",
        ]
        
        missing_imports = []
        for imp in required_imports:
            if imp not in content:
                missing_imports.append(imp)
        
        if missing_imports:
            print("❌ Faltan importaciones:")
            for imp in missing_imports:
                print(f"   • {imp}")
            return False
        
        print("✅ Archivo correcto")
        return True
        
    except Exception as e:
        print(f"❌ Error al leer archivo: {e}")
        return False

def check_imports():
    """Intenta importar los módulos principales."""
    print("\n🐍 VERIFICACIÓN DE IMPORTACIONES")
    print("=" * 50)
    
    # Agregar el directorio actual al path
    sys.path.insert(0, os.getcwd())
    
    modules_to_check = [
        ("app", "Paquete principal"),
        ("app.core", "Módulo core"),
        ("app.core.constantes", "Constantes"),
        ("app.core.recursos", "Recursos"),
        ("app.ui", "Módulo UI"),
        ("app.viewmodels", "ViewModels"),
    ]
    
    import_errors = []
    for module_name, description in modules_to_check:
        try:
            __import__(module_name)
            print(f"✅ {module_name} - {description}")
        except ImportError as e:
            print(f"❌ {module_name} - {description}")
            print(f"   Error: {e}")
            import_errors.append((module_name, str(e)))
    
    return len(import_errors) == 0

def check_dependencies():
    """Verifica las dependencias instaladas."""
    print("\n📦 VERIFICACIÓN DE DEPENDENCIAS")
    print("=" * 50)
    
    required_packages = [
        ("PySide6", "Framework GUI"),
        ("numpy", "Cálculo numérico"),
        ("pandas", "Manejo de datos"),
        ("matplotlib", "Gráficos"),
        ("scipy", "Estadística"),
        ("statsmodels", "Modelos estadísticos"),
    ]
    
    missing_packages = []
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} - {description}")
        except ImportError:
            print(f"❌ {package} - {description} (NO INSTALADO)")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def main():
    """Función principal de diagnóstico."""
    print("\n" + "=" * 60)
    print("  DIAGNÓSTICO - Comparador de Ozono v2.0")
    print("=" * 60)
    
    # Verificar que estamos en el directorio correcto
    if not Path("app").exists():
        print("\n❌ ERROR: No se encuentra la carpeta 'app'")
        print("   Ejecute este script desde el directorio raíz del proyecto")
        return 1
    
    # Ejecutar verificaciones
    checks = [
        ("Estructura", check_structure()),
        ("Archivos", check_files()),
        ("app/ui/__init__.py", check_ui_init()),
        ("Importaciones", check_imports()),
        ("Dependencias", check_dependencies()),
    ]
    
    # Resumen
    print("\n" + "=" * 60)
    print("  RESUMEN DEL DIAGNÓSTICO")
    print("=" * 60)
    
    all_passed = all(result for _, result in checks)
    
    for check_name, passed in checks:
        status = "✅ OK" if passed else "❌ FALLÓ"
        print(f"{check_name:.<30} {status}")
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("\n✅ TODOS LOS CHECKS PASARON")
        print("\nLa aplicación está lista para ejecutarse:")
        print("  python -m app.main")
    else:
        print("\n❌ HAY PROBLEMAS QUE RESOLVER")
        print("\nSugerencias:")
        
        if not checks[2][1]:  # app/ui/__init__.py falló
            print("\n1. Corrija app/ui/__init__.py:")
            print("   • Copie el archivo ui_init_fixed.py sobre app/ui/__init__.py")
            print("   • O ejecute: python fix_structure.py")
        
        if not checks[4][1]:  # Dependencias fallaron
            print("\n2. Instale las dependencias:")
            print("   pip install -r requirements.txt")
        
        print("\n3. Ejecute el script de corrección:")
        print("   python fix_structure.py")
    
    print("\n" + "=" * 60)
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
