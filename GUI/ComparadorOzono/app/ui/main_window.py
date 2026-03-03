# -*- coding: utf-8 -*-
"""
Ventana principal de la aplicación Comparador de Ozono.
"""

import os
import logging
from typing import Optional
from pathlib import Path # Añadido

import numpy as np
import pandas as pd  # Añadido
import matplotlib.image as mpimg  # fallback: cargar PNGs a Figure

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTextEdit, QMessageBox,
    QTabWidget, QToolBar, QStatusBar, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter
)

# === Matplotlib embebido (para tus gráficos existentes) ===
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# === Panel χ² en vivo (sin imágenes) ===
from .chi2_reales_panel import Chi2RealesPanel

# (Opcional) Panel que muestra PNGs ya generados por el runner
from .chi2_panel import Chi2Panel

# Panel de Validación de Supuestos
from .validation_panel import ValidationPanel
from .presentation_panel import PresentationPanel

# Núcleo de la app
# ...
from ..core.tema import ThemeManager
from ..core.constantes import (
    APP_NAME, APP_VERSION, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    MSG_NO_FILES, MSG_ANALYSIS_COMPLETE, MSG_ANALYSIS_ERROR,
    SHORTCUTS
)
from ..viewmodels.analisis_vm import AnalisisViewModel
from .dialog_about import DialogAbout
# ...

from ..core.stats_validator import AssumptionValidator # Importar validador

class ValidationWorker(QThread):
    """Thread para ejecutar validación masiva."""
    progreso = Signal(str)
    completado = Signal(pd.DataFrame)
    error = Signal(str)

    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = folder_path
        self.validator = AssumptionValidator()

    def run(self):
        try:
            self.progreso.emit(f"Escaneando directorio: {self.folder_path}")
            import glob
            from pathlib import Path
            
            # Buscar CSVs
            files = list(Path(self.folder_path).glob("*.csv"))
            if not files:
                raise FileNotFoundError("No se encontraron archivos CSV en el directorio.")
            
            self.progreso.emit(f"Procesando {len(files)} archivos...")
            df = self.validator.batch_process(files)
            
            # Guardar automáticamente en out_plots
            output_dir = Path("out_plots")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / "validation_results.csv"
            df.to_csv(output_path, index=False)
            
            self.completado.emit(df)
        except Exception as e:
            self.error.emit(str(e))

class WorkerThread(QThread):
    """Thread para ejecutar el análisis sin bloquear la UI."""
    progreso = Signal(str)
    completado = Signal(dict)
    error = Signal(str)

    def __init__(self, view_model: AnalisisViewModel):
        super().__init__()
        self.view_model = view_model

    def run(self):
        try:
            self.progreso.emit("Cargando archivos...")
            resultados = self.view_model.ejecutar_analisis()
            self.completado.emit(resultados)
        except Exception as e:
            self.error.emit(str(e))



class MainWindow(QMainWindow):
    """Ventana principal de la aplicación con diseño moderno y funcional."""

    def __init__(self):
        """Inicializa la ventana principal."""
        super().__init__()
        self.theme_manager = ThemeManager()
        self.view_model = AnalisisViewModel()

        # Atributos para gráficos embebidos existentes
        self.figuras = {}            # Dict[str, Figure]
        self.canvas = None           # FigureCanvas (si lo usas en otros módulos)
        self.toolbar = None          # NavigationToolbar
        self.tabs_graficos = None    # QTabWidget: un tab por gráfico
        self.label_graficos = None   # Label modo informativo

        # Panel χ² por PNG (opcional)
        self.tab_chi2_panel: Optional[Chi2Panel] = None
        
        # Panel de Validación
        self.tab_validation: Optional[ValidationPanel] = None

        # Panel de Presentación
        self.tab_presentation: Optional[PresentationPanel] = None
        
        self.validation_worker: Optional[ValidationWorker] = None

        self.worker_thread: Optional[WorkerThread] = None

        # Orden correcto de inicialización
        self.configurar_ventana()
        self.crear_acciones()
        self.crear_menu_toolbar()
        self.crear_interfaz()        # ← aquí se crea self.tabs y se añaden pestañas
        self.crear_status_bar()
        self.conectar_senales()

        # Cargar tema guardado
        self.theme_manager.cargar_tema_guardado()
        
        # Intentar cargar resultados de validación previos automáticamente
        self.cargar_validacion_automatica()
        
        logging.info("Ventana principal inicializada")

    def cargar_validacion_automatica(self):
        """
        Intenta cargar validation_results.csv. 
        Si no existe, intenta ejecutar la validación automáticamente sobre 'gui_mensual'.
        """
        path_results = Path("out_plots") / "validation_results.csv"
        
        # 1. Intentar cargar si existe
        if path_results.exists():
            try:
                df = pd.read_csv(path_results)
                req_cols = {'dataset_id', 'test_name', 'p_value'}
                if req_cols.issubset(df.columns) and self.tab_validation:
                    self.tab_validation.load_data(df)
                    logging.info(f"Resultados de validación cargados automáticamente desde {path_results}")
                    return
            except Exception as e:
                logging.warning(f"Error cargando validación existente: {e}")

        # 2. Si no existe (o falló), intentar ejecutar automáticamente
        from ..core.constantes import GUI_BASE_DIR
        data_dir = Path(GUI_BASE_DIR) / "gui_mensual"
        
        if data_dir.exists():
            # Verificar si hay CSVs
            if list(data_dir.glob("*.csv")):
                logging.info(f"Iniciando validación automática sobre {data_dir}")
                self.label_status.setText("Ejecutando validación inicial automática...")
                
                # Usar el worker existente
                self.validation_worker = ValidationWorker(str(data_dir))
                self.validation_worker.progreso.connect(lambda msg: self.label_status.setText(msg))
                self.validation_worker.completado.connect(self.on_validacion_completada)
                self.validation_worker.error.connect(self.on_error_ocurrido)
                self.validation_worker.start()
            else:
                logging.warning(f"Directorio {data_dir} existe pero no tiene CSVs.")
        else:
            logging.warning(f"No se encontró directorio de datos para auto-validación: {data_dir}")

    def configurar_ventana(self) -> None:
        """Configura las propiedades de la ventana principal."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(1200, 800)

        # Centrar ventana
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def crear_acciones(self) -> None:
        """Crea las acciones de la aplicación."""
        # Archivo
        self.action_cargar_real = QAction("&Cargar Datos Reales", self)
        self.action_cargar_real.setShortcut(QKeySequence(SHORTCUTS["open_real"]))
        self.action_cargar_real.setStatusTip("Cargar archivo CSV con datos reales de ozono")
        self.action_cargar_real.triggered.connect(self.cargar_archivo_real)

        self.action_cargar_pred = QAction("Cargar Datos &Predichos", self)
        self.action_cargar_pred.setShortcut(QKeySequence(SHORTCUTS["open_pred"]))
        self.action_cargar_pred.setStatusTip("Cargar archivo CSV con datos predichos de ozono")
        self.action_cargar_pred.triggered.connect(self.cargar_archivo_predicho)
        
        # Acción para cargar resultados de validación
        self.action_cargar_validacion = QAction("Cargar &Resultados Validación", self)
        self.action_cargar_validacion.setStatusTip("Cargar CSV con p-valores de validación de supuestos")
        self.action_cargar_validacion.triggered.connect(self.cargar_resultados_validacion)

        # Acción para ejecutar validación batch
        self.action_ejecutar_validacion = QAction("Ejecutar Validación (&Batch)", self)
        self.action_ejecutar_validacion.setStatusTip("Ejecutar validación estadística sobre un directorio de CSVs")
        self.action_ejecutar_validacion.triggered.connect(self.ejecutar_validacion_batch)

        self.action_ejecutar = QAction("&Ejecutar Análisis", self)
        self.action_ejecutar.setShortcut(QKeySequence(SHORTCUTS["run_analysis"]))
        self.action_ejecutar.setStatusTip("Ejecutar análisis de diagnóstico")
        self.action_ejecutar.triggered.connect(self.ejecutar_analisis)

        self.action_exportar = QAction("&Exportar Resultados", self)
        self.action_exportar.setShortcut(QKeySequence(SHORTCUTS["export_results"]))
        self.action_exportar.setStatusTip("Exportar resultados del análisis")
        self.action_exportar.triggered.connect(self.exportar_resultados)
        self.action_exportar.setEnabled(False)

        self.action_salir = QAction("&Salir", self)
        self.action_salir.setShortcut(QKeySequence(SHORTCUTS["quit"]))
        self.action_salir.setStatusTip("Salir de la aplicación")
        self.action_salir.triggered.connect(self.close)

        # Ver
        self.action_tema = QAction("Alternar &Tema", self)
        self.action_tema.setShortcut(QKeySequence(SHORTCUTS["toggle_theme"]))
        self.action_tema.setStatusTip("Cambiar entre tema claro y oscuro")
        self.action_tema.triggered.connect(self.alternar_tema)

        # Ayuda
        self.action_ayuda = QAction("&Manual de Usuario", self)
        self.action_ayuda.setShortcut(QKeySequence(SHORTCUTS["show_help"]))
        self.action_ayuda.setStatusTip("Mostrar manual de usuario")
        self.action_ayuda.triggered.connect(self.mostrar_ayuda)

        self.action_acerca = QAction("&Acerca de", self)
        self.action_acerca.setShortcut(QKeySequence(SHORTCUTS["show_about"]))
        self.action_acerca.setStatusTip("Información sobre la aplicación")
        self.action_acerca.triggered.connect(self.mostrar_acerca_de)

    def crear_menu_toolbar(self) -> None:
        """Crea la barra de menú y toolbar."""
        barra_menu = self.menuBar()

        menu_archivo = barra_menu.addMenu("&Archivo")
        menu_archivo.addAction(self.action_cargar_real)
        menu_archivo.addAction(self.action_cargar_pred)
        menu_archivo.addAction(self.action_cargar_validacion)
        menu_archivo.addAction(self.action_ejecutar_validacion) # Nueva acción
        menu_archivo.addSeparator()
        menu_archivo.addAction(self.action_ejecutar)
        menu_archivo.addAction(self.action_exportar)
        menu_archivo.addSeparator()
        menu_archivo.addAction(self.action_salir)

        menu_ver = barra_menu.addMenu("&Ver")
        menu_ver.addAction(self.action_tema)

        menu_ayuda = barra_menu.addMenu("&Ayuda")
        menu_ayuda.addAction(self.action_ayuda)
        menu_ayuda.addAction(self.action_acerca)

        # Toolbar eliminado por solicitud del usuario (redundante con menú)
        # self.toolbar_principal = QToolBar("Acciones")
        # ...

    def crear_interfaz(self) -> None:
        """Crea la interfaz principal de la aplicación."""
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)

        # Encabezado
        cabecera = QHBoxLayout()

        label_titulo = QLabel(f"{APP_NAME} v{APP_VERSION}")
        label_titulo.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        cabecera.addWidget(label_titulo)
        cabecera.addStretch()

        btn_ayuda = QPushButton("Ayuda")
        btn_ayuda.clicked.connect(self.mostrar_ayuda)
        cabecera.addWidget(btn_ayuda)

        btn_acerca = QPushButton("Acerca de")
        btn_acerca.clicked.connect(self.mostrar_acerca_de)
        cabecera.addWidget(btn_acerca)

        layout.addLayout(cabecera)

        # Tabs principales (¡se crea aquí!)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # Tab 1: Presentación (NUEVO - Reemplaza Resultados y Gráficos iniciales)
        self.tab_presentation = PresentationPanel(self)
        self.tabs.addTab(self.tab_presentation, "Presentación")

        # Tabs antiguos (Ocultos por solicitud del usuario)
        # self.crear_tab_resultados()
        # self.crear_tab_graficos()

        # Tab 2: χ² (Reales) — en vivo, sin imágenes
        self.tabs.addTab(Chi2RealesPanel(self), "χ² (Reales)")
        
        # Tab 3: Validación de Supuestos (NUEVO)
        self.tab_validation = ValidationPanel(self)
        self.tabs.addTab(self.tab_validation, "Validación Supuestos")

        # (Opcional) Tab 5: PNGs/tabla desde disco (si usas runner externo)
        try:
            self.tab_chi2_panel = Chi2Panel()  # sin kwargs para evitar TypeError
            self.tabs.addTab(self.tab_chi2_panel, "χ² / χ²_red (PNG)")
        except TypeError:
            self.tab_chi2_panel = None  # no bloquees la app si cambia la firma

        self.setCentralWidget(contenedor)

        # Estilos (simple)
        contenedor.setStyleSheet("""
            QLabel { color: #1a1a1a; }
            QTabWidget::pane { border: 1px solid #d0d0d0; }
            QTabBar::tab { padding: 8px 16px; }
        """)

    def crear_tab_resultados(self) -> None:
        """Crea el tab de resultados del análisis."""
        widget_resultados = QWidget()
        layout = QVBoxLayout(widget_resultados)

        # Botones de acción
        fila_botones = QHBoxLayout()
        self.btn_cargar_real = QPushButton("Cargar Reales")
        self.btn_cargar_real.clicked.connect(self.cargar_archivo_real)
        fila_botones.addWidget(self.btn_cargar_real)

        self.btn_cargar_pred = QPushButton("Cargar Predichos")
        self.btn_cargar_pred.clicked.connect(self.cargar_archivo_predicho)
        fila_botones.addWidget(self.btn_cargar_pred)

        self.btn_ejecutar = QPushButton("Ejecutar Análisis")
        self.btn_ejecutar.clicked.connect(self.ejecutar_analisis)
        fila_botones.addWidget(self.btn_ejecutar)

        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        # Splitter: tabla + resumen
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)

        # Tabla de resultados
        self.tabla_resultados = QTableWidget(0, 5)
        self.tabla_resultados.setHorizontalHeaderLabels(
            ["Prueba", "Estadístico", "GL", "p-valor", "Estado"]
        )
        self.tabla_resultados.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        splitter.addWidget(self.tabla_resultados)

        # Resumen / texto
        panel_texto = QWidget()
        vbox_texto = QVBoxLayout(panel_texto)

        label_resumen = QLabel("Resumen del análisis")
        label_resumen.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        vbox_texto.addWidget(label_resumen)

        self.texto_resumen = QTextEdit()
        self.texto_resumen.setReadOnly(True)
        vbox_texto.addWidget(self.texto_resumen, 1)

        splitter.addWidget(panel_texto)
        layout.addWidget(splitter, 1)

        self.tabs.addTab(widget_resultados, "📄 Resultados")

    def crear_tab_graficos(self) -> None:
        """Crea el tab para mostrar gráficos (un tab por figura, proporcional al tamaño de la ventana)."""
        widget_graficos = QWidget()
        vbox = QVBoxLayout(widget_graficos)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        # Tabs internos de gráficos
        self.tabs_graficos = QTabWidget()
        self.tabs_graficos.setTabsClosable(False)
        self.tabs_graficos.setDocumentMode(True)
        vbox.addWidget(self.tabs_graficos, 1)

        # Label informativo (modo legado si no hay figuras)
        self.label_graficos = QLabel()
        self.label_graficos.setWordWrap(True)
        self.label_graficos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_graficos.setText(
            "Los gráficos de diagnóstico se guardarán automáticamente\n"
            "en la carpeta 'out_plots' cuando ejecute el análisis.\n\n"
            "Gráficos generados esperados:\n"
            "• Histograma de residuales\n"
            "• Q-Q Plot\n"
            "• Función de Autocorrelación (ACF)\n"
            "• Scatter plot Real vs Predicho"
        )
        self.label_graficos.setStyleSheet(
            "QLabel { font-size: 14px; padding: 20px; "
            "background-color: rgba(46, 134, 171, 0.08); border-radius: 10px; }"
        )
        vbox.addWidget(self.label_graficos)

        # Estado inicial: sin figuras → mostrar label, ocultar tabs
        self.tabs_graficos.hide()
        self.label_graficos.show()

        self.tabs.addTab(widget_graficos, '📈 Gráficos')

    def _agregar_tab_figura(self, nombre: str, fig: Figure) -> None:
        """Crea un tab con toolbar + canvas para una figura específica."""
        page = QWidget()
        pv = QVBoxLayout(page)
        pv.setContentsMargins(0, 0, 0, 0)

        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)

        pv.addWidget(toolbar)
        pv.addWidget(canvas, 1)

        self.tabs_graficos.addTab(page, f"• {nombre}")

    def _fig_from_png(self, path: str) -> Optional[Figure]:
        """Crea una Figure desde un PNG guardado (modo legado)."""
        try:
            img = mpimg.imread(path)
            fig = Figure(constrained_layout=True)
            ax = fig.add_subplot(111)
            ax.imshow(img)
            ax.axis('off')
            return fig
        except Exception:
            logging.warning(f"No se pudo cargar PNG como figura: {path}")
            return None

    def crear_status_bar(self) -> None:
        """Crea la barra de estado."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Mensaje inicial
        self.label_status = QLabel("Listo")
        self.status_bar.addPermanentWidget(self.label_status)

        # Progress bar (oculto por defecto)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)

        # Label de tema actual
        self.label_tema = QLabel(f"Tema: {self.theme_manager.tema_actual}")
        self.status_bar.addPermanentWidget(self.label_tema)

    def conectar_senales(self) -> None:
        """Conecta las señales del ViewModel."""
        self.view_model.archivo_cargado.connect(self.on_archivo_cargado)
        self.view_model.analisis_completado.connect(self.on_analisis_completado)
        self.view_model.error_ocurrido.connect(self.on_error_ocurrido)

    @Slot(str)
    def on_archivo_cargado(self, ruta: str) -> None:
        """Maneja la señal de archivo cargado."""
        base = os.path.basename(ruta)
        if ruta.endswith("_real.csv"):
            self.label_status.setText(f"Archivo real cargado: {base}")
        elif ruta.endswith("_pred.csv"):
            self.label_status.setText(f"Archivo predicho cargado: {base}")
        else:
            self.label_status.setText(f"Archivo cargado: {base}")

    @Slot(dict)
    def on_analisis_completado(self, resultados: dict) -> None:
        """Maneja la señal de análisis completado."""
        # Llenar tabla de resultados
        pruebas = resultados.get("pruebas", [])
        self.tabla_resultados.setRowCount(len(pruebas))

        for i, prueba in enumerate(pruebas):
            # Nombre de la prueba
            self.tabla_resultados.setItem(i, 0, QTableWidgetItem(prueba.nombre))

            # Estadístico
            if prueba.estadistico is not None and not np.isnan(prueba.estadistico):
                texto_est = f"{prueba.estadistico:.6g}"
            else:
                texto_est = "-"
            self.tabla_resultados.setItem(i, 1, QTableWidgetItem(texto_est))

            # Grados de libertad
            if prueba.grados_libertad is not None:
                texto_gl = str(int(prueba.grados_libertad))
            else:
                texto_gl = "-"
            self.tabla_resultados.setItem(i, 2, QTableWidgetItem(texto_gl))

            # p-valor
            if prueba.p_valor is not None and not np.isnan(prueba.p_valor):
                texto_p = f"{prueba.p_valor:.6g}"
            else:
                texto_p = "-"
            self.tabla_resultados.setItem(i, 3, QTableWidgetItem(texto_p))

            # Estado
            estado = "✅" if prueba.es_exitoso else "❌"
            item_estado = QTableWidgetItem(estado)
            item_estado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla_resultados.setItem(i, 4, item_estado)

        # Mostrar resumen
        conclusion = resultados.get("conclusion", "")
        rutas = resultados.get("rutas_graficos", {})

        texto_resumen = conclusion
        if rutas:
            texto_resumen += "\n\nGráficos guardados:\n" + "\n".join(
                f"• {k}: {v}" for k, v in rutas.items()
            )
        self.texto_resumen.setText(texto_resumen)

        # Manejo de figuras embebidas (existente)
        self.figuras = resultados.get("figuras", {}) or {}
        rutas = resultados.get("rutas_graficos", {}) or {}

        # Limpiar tabs previos
        while self.tabs_graficos.count() > 0:
            w = self.tabs_graficos.widget(0)
            self.tabs_graficos.removeTab(0)
            w.deleteLater()

        if isinstance(self.figuras, dict) and len(self.figuras) > 0:
            # Orden sugerido de pestañas
            orden_sugerido = ["histograma", "qq_plot", "acf", "scatter"]
            disponibles = [k for k in orden_sugerido if k in self.figuras] + \
                          [k for k in self.figuras.keys() if k not in orden_sugerido]

            for nombre in disponibles:
                self._agregar_tab_figura(nombre, self.figuras[nombre])

            # Mostrar tabs y ocultar label informativo
            self.label_graficos.hide()
            self.tabs_graficos.show()
        else:
            # Fallback: si no hay figuras pero sí PNGs guardados, conviértelos a Figure
            figs_from_png = {}
            for nombre, path in rutas.items():
                f = self._fig_from_png(path)
                if f is not None:
                    figs_from_png[nombre] = f

            if figs_from_png:
                for nombre, fig in figs_from_png.items():
                    self._agregar_tab_figura(nombre, fig)
                self.label_graficos.hide()
                self.tabs_graficos.show()
            else:
                self.tabs_graficos.hide()
                self.label_graficos.show()

        # Refrescar el panel χ² por si hay salidas nuevas en disco (CSV)
        if self.tab_chi2_panel is not None:
            try:
                self.tab_chi2_panel.refresh()
            except Exception as _e:
                logging.warning("No se pudo refrescar el panel χ² (PNG): %s", _e)

        # Actualizar UI
        self.progress_bar.hide()
        self.label_status.setText(MSG_ANALYSIS_COMPLETE)
        self.action_exportar.setEnabled(True)

        # Cambiar al tab de resultados
        self.tabs.setCurrentIndex(0)

        # Mensaje de éxito
        QMessageBox.information(self, "Análisis Completado", f"{MSG_ANALYSIS_COMPLETE}")

    @Slot(str)
    def on_error_ocurrido(self, mensaje: str) -> None:
        """Maneja errores del ViewModel."""
        self.progress_bar.hide()
        self.label_status.setText(MSG_ANALYSIS_ERROR)
        QMessageBox.critical(self, "Error", mensaje)
        logging.error(f"Error en análisis: {mensaje}")

    def alternar_tema(self) -> None:
        """Alterna entre tema claro y oscuro."""
        nuevo_tema = self.theme_manager.alternar_tema()
        self.label_tema.setText(f"Tema: {nuevo_tema}")
        logging.info(f"Tema cambiado a: {nuevo_tema}")

    def mostrar_ayuda(self) -> None:
        """Muestra la ayuda de la aplicación."""
        QMessageBox.information(
            self,
            "Ayuda",
            "1) Carga los CSV de reales y predichos.\n"
            "2) Ejecuta el análisis.\n"
            "3) Revisa resultados y gráficos.\n"
            "4) Exporta si lo deseas."
        )

    def mostrar_acerca_de(self) -> None:
        """Muestra el diálogo Acerca de."""
        dlg = DialogAbout(self)
        dlg.exec()

    def cargar_archivo_real(self) -> None:
        """Abre diálogo para cargar archivo de datos reales."""
        archivo, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de datos reales",
            "",
            "Archivos CSV (*.csv);;Todos los archivos (*.*)"
        )
        if archivo:
            self.view_model.cargar_archivo_real(archivo)

    def cargar_archivo_predicho(self) -> None:
        """Abre diálogo para cargar archivo de datos predichos."""
        archivo, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de datos predichos",
            "",
            "Archivos CSV (*.csv);;Todos los archivos (*.*)"
        )
        if archivo:
            self.view_model.cargar_archivo_predicho(archivo)

    def cargar_resultados_validacion(self) -> None:
        """Carga un archivo CSV con resultados de validación (p-valores)."""
        archivo, _ = QFileDialog.getOpenFileName(
            self,
            "Cargar Resultados de Validación",
            "",
            "Archivos CSV (*.csv);;Todos los archivos (*.*)"
        )
        if archivo:
            try:
                df = pd.read_csv(archivo)
                # Verificar columnas mínimas
                req_cols = {'dataset_id', 'test_name', 'p_value'}
                if not req_cols.issubset(df.columns):
                    # Intentar adaptar si tiene otro formato (ej: salida de R directa)
                    # Por ahora asumimos formato correcto o lanzamos error
                    raise ValueError(f"El archivo debe tener columnas: {req_cols}")
                
                if self.tab_validation:
                    self.tab_validation.load_data(df)
                    self.tabs.setCurrentWidget(self.tab_validation)
                    self.label_status.setText(f"Validación cargada: {os.path.basename(archivo)}")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error de Carga", f"No se pudo cargar el archivo:\n{e}")

    def ejecutar_analisis(self) -> None:
        """Ejecuta el análisis de diagnóstico."""
        if not self.view_model.archivos_listos():
            QMessageBox.warning(self, "Atención", MSG_NO_FILES)
            return

        # Mostrar progreso
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)  # Indeterminado
        self.label_status.setText("Ejecutando análisis...")

        # Thread de trabajo
        self.worker_thread = WorkerThread(self.view_model)
        self.worker_thread.progreso.connect(lambda msg: self.label_status.setText(msg))
        self.worker_thread.completado.connect(self.on_analisis_completado)
        self.worker_thread.error.connect(self.on_error_ocurrido)
        self.worker_thread.start()

    def exportar_resultados(self) -> None:
        """Exporta los resultados del análisis."""
        archivo, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar resultados",
            "resultados_analisis.txt",
            "Archivos de texto (*.txt);;CSV (*.csv)"
        )
        if archivo:
            try:
                self.view_model.exportar_resultados(archivo)
                QMessageBox.information(
                    self,
                    "Exportación completada",
                    f"Resultados exportados a:\n{archivo}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error al exportar", str(e))

    def closeEvent(self, event) -> None:
        """Maneja el evento de cierre de la ventana."""
        respuesta = QMessageBox.question(
            self,
            "Confirmar salida",
            "¿Está seguro de que desea salir?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if respuesta == QMessageBox.StandardButton.Yes:
            logging.info("Aplicación cerrada por el usuario")
            event.accept()
        else:
            event.ignore()

    def ejecutar_validacion_batch(self) -> None:
        """Ejecuta la validación estadística sobre un directorio."""
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar directorio con CSVs")
        if folder:
            self.progress_bar.show()
            self.progress_bar.setRange(0, 0)
            self.label_status.setText("Iniciando validación masiva...")
            
            self.validation_worker = ValidationWorker(folder)
            self.validation_worker.progreso.connect(lambda msg: self.label_status.setText(msg))
            self.validation_worker.completado.connect(self.on_validacion_completada)
            self.validation_worker.error.connect(self.on_error_ocurrido)
            self.validation_worker.start()

    def on_validacion_completada(self, df: pd.DataFrame) -> None:
        """Maneja la finalización de la validación batch."""
        self.progress_bar.hide()
        self.label_status.setText("Validación completada.")
        
        if self.tab_validation:
            self.tab_validation.load_data(df)
            self.tabs.setCurrentWidget(self.tab_validation)
        
        QMessageBox.information(self, "Éxito", 
            f"Se procesaron {len(df['dataset_id'].unique())} conjuntos de datos.\n"
            f"Resultados guardados en 'out_plots/validation_results.csv' y se cargarán automáticamente la próxima vez."
        )

