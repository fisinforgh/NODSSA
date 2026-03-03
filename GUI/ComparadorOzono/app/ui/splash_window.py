"""
Ventana de presentación (Splash Screen) de la aplicación.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGraphicsOpacityEffect, QApplication
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QPropertyAnimation,
    QEasingCurve
)
from PySide6.QtGui import QPixmap, QFont, QPainter, QBrush, QColor

from ..core.recursos import ResourceManager
from ..core.constantes import APP_NAME, APP_VERSION, ORGANIZATION


def _qt_flag(enum_group_name: str, member_name: str):
    """
    Obtiene de forma segura un flag de Qt soportando tanto PySide6 reciente (Qt.WindowType)
    como variantes donde el miembro vive en Qt (Qt.FramelessWindowHint).
    """
    # Intentar Qt.WindowType.FramelessWindowHint, etc.
    enum_group = getattr(Qt, enum_group_name, None)
    if enum_group is not None and hasattr(enum_group, member_name):
        return getattr(enum_group, member_name)
    # Fallback: Qt.FramelessWindowHint, Qt.AlignCenter, etc.
    return getattr(Qt, member_name)


class SplashWindow(QWidget):
    """Ventana de presentación con animaciones y diseño moderno."""

    ingreso_solicitado = Signal()

    def __init__(self):
        super().__init__()
        self.configurar_ventana()
        self.crear_interfaz()
        self.iniciar_animaciones()

    def configurar_ventana(self) -> None:
        """Configura las propiedades de la ventana."""
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(800, 600)

        # --- FIX principal: usar WindowType/Fallback en PySide6 ---
        frameless = _qt_flag("WindowType", "FramelessWindowHint")
        self.setWindowFlags(frameless)

        # Translucencia con compatibilidad
        wa_translucent = _qt_flag("WidgetAttribute", "WA_TranslucentBackground")
        self.setAttribute(wa_translucent)

        # Centrar en la pantalla principal (robusto multi-monitor)
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)

    def crear_interfaz(self) -> None:
        """Crea la interfaz de la ventana splash."""
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(0, 0, 0, 0)

        # Contenedor con fondo
        self.contenedor = QWidget()
        self.contenedor.setObjectName("splashContainer")
        self.contenedor.setStyleSheet("""
            #splashContainer {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e3c72,
                    stop:0.5 #2e5499,
                    stop:1 #2e86ab
                );
                border-radius: 20px;
            }
        """)

        layout_contenedor = QVBoxLayout(self.contenedor)
        layout_contenedor.setSpacing(20)
        layout_contenedor.setContentsMargins(50, 50, 50, 50)

        layout_contenedor.addStretch(1)

        # Logo
        self.label_logo = QLabel()
        self.label_logo.setAlignment(_qt_flag("AlignmentFlag", "AlignCenter"))
        logo_path = ResourceManager.get_logo()
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            pixmap = pixmap.scaled(
                200, 200,
                _qt_flag("AspectRatioMode", "KeepAspectRatio"),
                _qt_flag("TransformationMode", "SmoothTransformation")
            )
            self.label_logo.setPixmap(pixmap)
        else:
            self.label_logo.setText("UNAL")
            font = QFont("Arial", 48, QFont.Weight.Bold)
            self.label_logo.setFont(font)
            self.label_logo.setStyleSheet("color: white;")
        layout_contenedor.addWidget(self.label_logo)

        # Título
        self.label_titulo = QLabel(APP_NAME)
        self.label_titulo.setAlignment(_qt_flag("AlignmentFlag", "AlignCenter"))
        font_titulo = QFont("Arial", 32, QFont.Weight.Bold)
        self.label_titulo.setFont(font_titulo)
        self.label_titulo.setStyleSheet("color: white; padding: 20px;")
        layout_contenedor.addWidget(self.label_titulo)

        # Subtítulo
        self.label_subtitulo = QLabel("Análisis Comparativo de Datos de Ozono")
        self.label_subtitulo.setAlignment(_qt_flag("AlignmentFlag", "AlignCenter"))
        font_subtitulo = QFont("Arial", 14)
        self.label_subtitulo.setFont(font_subtitulo)
        self.label_subtitulo.setStyleSheet("color: #E0E0E0; padding: 5px;")
        layout_contenedor.addWidget(self.label_subtitulo)

        # Versión
        self.label_version = QLabel(f"Versión {APP_VERSION}")
        self.label_version.setAlignment(_qt_flag("AlignmentFlag", "AlignCenter"))
        font_version = QFont("Arial", 10)
        self.label_version.setFont(font_version)
        self.label_version.setStyleSheet("color: #B0B0B0;")
        layout_contenedor.addWidget(self.label_version)

        layout_contenedor.addStretch(1)

        # Botón de ingreso
        self.boton_ingresar = QPushButton("INGRESAR")
        self.boton_ingresar.setFixedSize(200, 50)
        self.boton_ingresar.setCursor(_qt_flag("CursorShape", "PointingHandCursor"))
        self.boton_ingresar.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #2e5499;
                border: none;
                border-radius: 25px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover { background-color: #F0F0F0; }
            QPushButton:pressed { background-color: #E0E0E0; }
        """)
        self.boton_ingresar.clicked.connect(self.on_ingresar_clicked)

        layout_boton = QHBoxLayout()
        layout_boton.addStretch()
        layout_boton.addWidget(self.boton_ingresar)
        layout_boton.addStretch()
        layout_contenedor.addLayout(layout_boton)

        layout_contenedor.addStretch(1)

        # Universidad
        self.label_universidad = QLabel(ORGANIZATION)
        self.label_universidad.setAlignment(_qt_flag("AlignmentFlag", "AlignCenter"))
        font_universidad = QFont("Arial", 10)
        self.label_universidad.setFont(font_universidad)
        self.label_universidad.setStyleSheet("color: #B0B0B0;")
        layout_contenedor.addWidget(self.label_universidad)

        layout_principal.addWidget(self.contenedor)

        # Efecto de opacidad
        self.opacity_effect = QGraphicsOpacityEffect()
        self.contenedor.setGraphicsEffect(self.opacity_effect)

    def iniciar_animaciones(self) -> None:
        """Inicia las animaciones de entrada."""
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(1000)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.start()

        # Animación del botón (aparece después)
        self.boton_ingresar.hide()
        QTimer.singleShot(800, self.mostrar_boton_animado)

    def mostrar_boton_animado(self) -> None:
        """Muestra el botón con animación."""
        self.boton_ingresar.show()
        boton_opacity = QGraphicsOpacityEffect()
        self.boton_ingresar.setGraphicsEffect(boton_opacity)
        self.boton_animation = QPropertyAnimation(boton_opacity, b"opacity")
        self.boton_animation.setDuration(500)
        self.boton_animation.setStartValue(0.0)
        self.boton_animation.setEndValue(1.0)
        self.boton_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.boton_animation.start()

    def on_ingresar_clicked(self) -> None:
        """Maneja el evento de click en el botón ingresar."""
        self.fade_out_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_animation.setDuration(300)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InQuad)
        self.fade_out_animation.finished.connect(self.ingreso_solicitado.emit)
        self.fade_out_animation.start()

    def paintEvent(self, event) -> None:
        """Dibuja un fondo con sombra suave y esquinas redondeadas."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Sombra
        shadow_rect = self.rect().adjusted(10, 10, -10, -10)
        painter.setBrush(QBrush(QColor(0, 0, 0, 30)))
        painter.setPen(_qt_flag("PenStyle", "NoPen"))
        painter.drawRoundedRect(shadow_rect, 20, 20)

