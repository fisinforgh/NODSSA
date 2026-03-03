#!/usr/bin/env python3
"""
Script para corregir problemas de estructura y configuración del proyecto ComparadorOzono.
"""

import os
import shutil
from pathlib import Path

def main():
    """Corrige problemas comunes de instalación y estructura."""
    
    print("=" * 60)
    print("  Corrector de Estructura - Comparador de Ozono v2.0")
    print("=" * 60)
    print()
    
    # Verificar que estamos en el directorio correcto
    if not Path("app").exists():
        print("❌ Error: Ejecute este script desde el directorio raíz del proyecto")
        print("   (donde está la carpeta 'app')")
        return
    
    fixes_applied = []
    
    # 1. Corregir app/ui/__init__.py
    print("1. Verificando app/ui/__init__.py...")
    ui_init = Path("app/ui/__init__.py")
    
    correct_content = '''"""
Módulo de interfaz de usuario de la aplicación.
"""

from .splash_window import SplashWindow
from .main_window import MainWindow
from .dialog_about import DialogAbout

__all__ = [
    'SplashWindow',
    'MainWindow',
    'DialogAbout',
]
'''
    
    with open(ui_init, 'w', encoding='utf-8') as f:
        f.write(correct_content)
    print("   ✅ Archivo app/ui/__init__.py corregido")
    fixes_applied.append("app/ui/__init__.py corregido")
    
    # 2. Mover archivos de test/ a la raíz si están mal ubicados
    if Path("test").exists() and not Path("tests").exists():
        print("\n2. Renombrando directorio test/ a tests/...")
        shutil.move("test", "tests")
        print("   ✅ Directorio renombrado a tests/")
        fixes_applied.append("Directorio test/ renombrado a tests/")
    
    # 3. Mover archivos mal ubicados a la raíz
    print("\n3. Verificando ubicación de archivos...")
    files_to_move = {
        "tests/pytest.ini": "pytest.ini",
        "tests/run.sh": "run.sh",
        "tests/run.bat": "run.bat",
        "test/pytest.ini": "pytest.ini",
        "test/run.sh": "run.sh",
        "test/run.bat": "run.bat",
    }
    
    for source, dest in files_to_move.items():
        if Path(source).exists() and not Path(dest).exists():
            shutil.move(source, dest)
            print(f"   ✅ Movido {source} → {dest}")
            fixes_applied.append(f"Movido {source} a {dest}")
            
            # Hacer ejecutable run.sh si existe
            if dest == "run.sh" and os.name != 'nt':
                os.chmod(dest, 0o755)
                print(f"      ✅ run.sh marcado como ejecutable")
    
    # 4. Crear directorios faltantes
    print("\n4. Verificando directorios necesarios...")
    dirs_needed = [
        "app/assets",
        "app/styles",
        "sample_data",
    ]
    
    for dir_path in dirs_needed:
        if not Path(dir_path).exists():
            Path(dir_path).mkdir(parents=True)
            print(f"   ✅ Creado directorio {dir_path}")
            fixes_applied.append(f"Creado directorio {dir_path}")
    
    # 5. Verificar archivos de estilos
    print("\n5. Verificando archivos de estilos...")
    
    # Si no existen los archivos de estilos, crear versiones básicas
    if not Path("app/styles/theme_dark.qss").exists():
        with open("app/styles/theme_dark.qss", 'w') as f:
            f.write("/* Tema oscuro - archivo creado automáticamente */\n")
        print("   ✅ Creado app/styles/theme_dark.qss")
        fixes_applied.append("Creado archivo theme_dark.qss")
    
    if not Path("app/styles/theme_light.qss").exists():
        with open("app/styles/theme_light.qss", 'w') as f:
            f.write("/* Tema claro - archivo creado automáticamente */\n")
        print("   ✅ Creado app/styles/theme_light.qss")
        fixes_applied.append("Creado archivo theme_light.qss")
    
    # 6. Crear archivos de assets si no existen
    print("\n6. Verificando archivos de assets...")
    
    if not Path("app/assets/logo_universidad.png").exists():
        # Crear un PNG mínimo como placeholder
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (100, 100), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((10, 40), "UNAL", fill='black')
            img.save("app/assets/logo_universidad.png")
            print("   ✅ Creado logo_universidad.png (placeholder)")
            fixes_applied.append("Creado logo placeholder")
        except ImportError:
            print("   ⚠️  No se pudo crear logo (instale Pillow si lo necesita)")
    
    if not Path("app/assets/icon.png").exists():
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (64, 64), color='blue')
            draw = ImageDraw.Draw(img)
            draw.text((20, 20), "O3", fill='white')
            img.save("app/assets/icon.png")
            print("   ✅ Creado icon.png (placeholder)")
            fixes_applied.append("Creado ícono placeholder")
        except ImportError:
            print("   ⚠️  No se pudo crear ícono (instale Pillow si lo necesita)")
    
    # 7. Verificar requirements.txt
    print("\n7. Verificando requirements.txt...")
    if Path("Requirements.txt").exists() and not Path("requirements.txt").exists():
        shutil.move("Requirements.txt", "requirements.txt")
        print("   ✅ Renombrado Requirements.txt → requirements.txt")
        fixes_applied.append("Renombrado Requirements.txt")
    
    # 8. Verificar README.md
    if Path("Readme.md").exists() and not Path("README.md").exists():
        shutil.move("Readme.md", "README.md")
        print("   ✅ Renombrado Readme.md → README.md")
        fixes_applied.append("Renombrado Readme.md")
    
    # Resumen
    print("\n" + "=" * 60)
    print("  RESUMEN DE CORRECCIONES")
    print("=" * 60)
    
    if fixes_applied:
        print(f"\n✅ Se aplicaron {len(fixes_applied)} correcciones:")
        for fix in fixes_applied:
            print(f"   • {fix}")
    else:
        print("\n✅ No se encontraron problemas para corregir")
    
    print("\n" + "=" * 60)
    print("  PRÓXIMOS PASOS")
    print("=" * 60)
    print()
    print("1. Instale las dependencias:")
    print("   pip install -r requirements.txt")
    print()
    print("2. Ejecute la aplicación:")
    print("   python -m app.main")
    print()
    print("O use el script de ejecución:")
    print("   ./run.sh  (Linux/Mac)")
    print("   run.bat   (Windows)")
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()
