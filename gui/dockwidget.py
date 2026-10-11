"""
AquaRed - Panel Principal de Control (QDockWidget)
==================================================
Interfaz gráfica interactiva para el diseño integral de redes de agua potable.
Incluye:
 - Selector de Perfiles de Configuración (Red Urbana, Red Rural, Guardar/Cargar JSON).
 - Conmutación síncrona Urbano / Rural (dotación, presiones normativas y diámetros mínimos).
 - Selectores de capas del proyecto con filtrado de geometría.
 - Asistente de Auto-Snapping y edición topológica.
 - Ejecución paso a paso o flujo completo automatizado con reporte en vivo.
"""

import os
from PyQt5.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QComboBox,
    QDoubleSpinBox,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor

from qgis.core import (
    QgsProject,
    QgsMapLayerProxyModel,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsGeometry
)
from qgis.gui import QgsMapLayerComboBox

from ..core.idaan_rules import NORMAS, obtener_parametros_norma, CATALOGO_TUBERIAS
from ..core.profile_manager import (
    obtener_perfil_predeterminado,
    guardar_perfil_a_archivo,
    cargar_perfil_desde_archivo,
    PERFIL_RURAL_MINSA
)
from .snapping_manager import SnappingManager

class AquaRedDockWidget(QDockWidget):
    solicitar_ejecucion_paso = pyqtSignal(int)
    solicitar_ejecucion_completa = pyqtSignal()
    solicitar_ayuda = pyqtSignal()

    def __init__(self, iface, parent=None):
        super().__init__("AquaRed - Diseñador de Redes de Agua Potable", parent)
        self.iface = iface
        self.setObjectName("AquaRedDockWidget")

        self.init_ui()
        self.conectar_eventos()
        self.aplicar_perfil(obtener_perfil_predeterminado())

    def init_ui(self):
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # 1. ENCABEZADO Y PERFIL
        grp_perfil = QGroupBox("1. Perfil y Clasificación Normativa")
        layout_perfil = QVBoxLayout(grp_perfil)

        # Selector de perfil predeterminado
        h_prof = QHBoxLayout()
        h_prof.addWidget(QLabel("Perfil:"))
        self.cmb_perfil = QComboBox()
        self.cmb_perfil.addItems([
            "Red Urbana / Residencial (Norma IDAAN 100 gal)",
            "Red Rural / Comunitaria (Norma MINSA 80 gal)",
            "Personalizado..."
        ])
        self.cmb_perfil.setToolTip("Selecciona una plantilla predeterminada (Urbana o Rural) o usa 'Personalizado...'")
        h_prof.addWidget(self.cmb_perfil)
        layout_perfil.addLayout(h_prof)

        # Botones de Cargar / Guardar JSON
        h_json_btns = QHBoxLayout()
        self.btn_cargar_json = QPushButton("📂 Cargar JSON")
        self.btn_cargar_json.setToolTip("Carga un archivo de perfil de diseño .json previamente guardado o personalizado")
        self.btn_guardar_json = QPushButton("💾 Guardar JSON")
        self.btn_guardar_json.setToolTip("Exporta todos los valores actuales del panel (dotación, offset, zanja, diámetros) a un archivo .json portable")
        h_json_btns.addWidget(self.btn_cargar_json)
        h_json_btns.addWidget(self.btn_guardar_json)
        layout_perfil.addLayout(h_json_btns)

        # CONMUTADOR URBANO / RURAL (Síncrono)
        h_tipo = QHBoxLayout()
        h_tipo.addWidget(QLabel("Tipo de Zona:"))
        self.rb_urbano = QRadioButton("Urbano (IDAAN)")
        self.rb_rural = QRadioButton("Rural (MINSA)")
        self.rb_urbano.setChecked(True)
        self.tipo_group = QButtonGroup(self)
        self.tipo_group.addButton(self.rb_urbano, 1)
        self.tipo_group.addButton(self.rb_rural, 2)
        h_tipo.addWidget(self.rb_urbano)
        h_tipo.addWidget(self.rb_rural)
        layout_perfil.addLayout(h_tipo)

        # Campos dependientes de la norma
        form_norma = QFormLayout()
        self.spn_dotacion = QDoubleSpinBox()
        self.spn_dotacion.setRange(20.0, 300.0)
        self.spn_dotacion.setValue(100.0)
        self.spn_dotacion.setSuffix(" gal/hab/día")

        self.lbl_presion_min = QLabel("20.0 psi (14.06 mca)")
        self.lbl_presion_min.setStyleSheet("font-weight: bold; color: #0066cc;")

        self.cmb_diam_troncal = QComboBox()
        self.cmb_diam_troncal.addItems(['4"', '3"', '2.5"', '2"'])
        self.cmb_diam_ramal = QComboBox()
        self.cmb_diam_ramal.addItems(['3"', '2.5"', '2"'])

        self.spn_fmh = QDoubleSpinBox()
        self.spn_fmh.setRange(1.0, 4.0)
        self.spn_fmh.setSingleStep(0.05)
        self.spn_fmh.setValue(2.00)

        form_norma.addRow("Dotación Normativa:", self.spn_dotacion)
        form_norma.addRow("Presión Mínima Requerida:", self.lbl_presion_min)
        form_norma.addRow("Diámetro Mín. Troncal:", self.cmb_diam_troncal)
        form_norma.addRow("Diámetro Mín. Ramal:", self.cmb_diam_ramal)
        form_norma.addRow("Factor Pico (FMH):", self.spn_fmh)
        layout_perfil.addLayout(form_norma)

        layout.addWidget(grp_perfil)

        # 2. CAPAS DEL PROYECTO
        grp_capas = QGroupBox("2. Capas del Proyecto")
        form_capas = QFormLayout(grp_capas)

        self.cmb_layer_calles = QgsMapLayerComboBox()
        self.cmb_layer_calles.setFilters(QgsMapLayerProxyModel.LineLayer)

        self.cmb_layer_casas = QgsMapLayerComboBox()
        self.cmb_layer_casas.setFilters(QgsMapLayerProxyModel.PointLayer | QgsMapLayerProxyModel.PolygonLayer)

        self.cmb_layer_dem = QgsMapLayerComboBox()
        self.cmb_layer_dem.setFilters(QgsMapLayerProxyModel.RasterLayer)

        self.cmb_layer_tanque = QgsMapLayerComboBox()
        self.cmb_layer_tanque.setFilters(QgsMapLayerProxyModel.PointLayer)

        form_capas.addRow("Ejes Viales / Calles:", self.cmb_layer_calles)
        form_capas.addRow("Viviendas / Huellas:", self.cmb_layer_casas)
        form_capas.addRow("Ráster DEM:", self.cmb_layer_dem)
        form_capas.addRow("Tanque / Fuente:", self.cmb_layer_tanque)
        layout.addWidget(grp_capas)

        # 3. PARÁMETROS GEOMÉTRICOS Y ZANJA
        grp_geom = QGroupBox("3. Parámetros Geométricos y Zanja")
        form_geom = QFormLayout(grp_geom)

        self.spn_offset = QDoubleSpinBox()
        self.spn_offset.setRange(0.5, 20.0)
        self.spn_offset.setValue(5.00)
        self.spn_offset.setSuffix(" m")

        self.spn_prof_zanja = QDoubleSpinBox()
        self.spn_prof_zanja.setRange(0.5, 3.0)
        self.spn_prof_zanja.setValue(1.15)
        self.spn_prof_zanja.setSuffix(" m")

        self.spn_h_torre = QDoubleSpinBox()
        self.spn_h_torre.setRange(0.0, 50.0)
        self.spn_h_torre.setValue(15.00)
        self.spn_h_torre.setSuffix(" m")

        self.spn_tolerancia_snap = QDoubleSpinBox()
        self.spn_tolerancia_snap.setRange(0.1, 5.0)
        self.spn_tolerancia_snap.setValue(0.75)
        self.spn_tolerancia_snap.setSuffix(" m")

        form_geom.addRow("Offset Vial Paralelo:", self.spn_offset)
        form_geom.addRow("Profundidad de Zanja:", self.spn_prof_zanja)
        form_geom.addRow("Altura Torre Tanque:", self.spn_h_torre)
        form_geom.addRow("Tolerancia Snapping:", self.spn_tolerancia_snap)
        layout.addWidget(grp_geom)

        # 4. HERRAMIENTAS DE EDICIÓN Y SNAPPING
        grp_snap = QGroupBox("4. Herramientas de Edición y Snapping")
        layout_snap = QVBoxLayout(grp_snap)
        self.btn_config_snap = QPushButton("🧲 Configurar Auto-Snapping y Topología")
        self.btn_config_snap.setToolTip("Configura auto-ensamblado en vértices, segmentos e intersecciones y activa edición topológica")
        layout_snap.addWidget(self.btn_config_snap)
        layout.addWidget(grp_snap)

        # 5. EJECUCIÓN DEL FLUJO DE TRABAJO
        grp_ejec = QGroupBox("5. Flujo de Diseño Hidráulico")
        layout_ejec = QVBoxLayout(grp_ejec)

        self.btn_step1 = QPushButton("Paso 1: Extraer Calles y Viviendas")
        self.btn_step2 = QPushButton("Paso 2: Muestrear Elevaciones DEM")
        self.btn_step3 = QPushButton("Paso 3: Trazar Tuberías con Offset")
        self.btn_step4 = QPushButton("Paso 4: Trazar Acometidas")
        self.btn_step5 = QPushButton("Paso 5: Asignar Demandas (Tramo IDAAN)")
        self.btn_step6 = QPushButton("Paso 6: Validar Topología y Válvulas")
        self.btn_step7 = QPushButton("Paso 7: Exportar a EPANET (.INP)")

        layout_ejec.addWidget(self.btn_step1)
        layout_ejec.addWidget(self.btn_step2)
        layout_ejec.addWidget(self.btn_step3)
        layout_ejec.addWidget(self.btn_step4)
        layout_ejec.addWidget(self.btn_step5)
        layout_ejec.addWidget(self.btn_step6)
        layout_ejec.addWidget(self.btn_step7)

        # Botón Maestro de Ejecución Completa
        self.btn_ejecutar_todo = QPushButton("⚡ EJECUTAR FLUJO COMPLETO")
        self.btn_ejecutar_todo.setStyleSheet(
            "QPushButton { background-color: #007acc; color: white; font-weight: bold; font-size: 13px; padding: 10px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #005999; }"
        )
        layout_ejec.addWidget(self.btn_ejecutar_todo)
        layout.addWidget(grp_ejec)

        # 6. LOG DE AUDITORÍA Y ESTADO
        grp_log = QGroupBox("6. Auditoría y Diagnóstico en Vivo")
        layout_log = QVBoxLayout(grp_log)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMinimumHeight(140)
        self.txt_log.setStyleSheet("background-color: #f7f9fa; font-family: Consolas, monospace; font-size: 11px;")
        layout_log.addWidget(self.txt_log)

        # Botón de Ayuda
        self.btn_ayuda = QPushButton("ℹ️ Guía Técnica y Normativa IDAAN")
        layout_log.addWidget(self.btn_ayuda)
        layout.addWidget(grp_log)

        scroll_area.setWidget(main_widget)
        self.setWidget(scroll_area)

    def conectar_eventos(self):
        self.rb_urbano.toggled.connect(self.actualizar_clasificacion_ui)
        self.rb_rural.toggled.connect(self.actualizar_clasificacion_ui)
        self.cmb_perfil.currentIndexChanged.connect(self.on_cambio_perfil_combo)
        self.btn_guardar_json.clicked.connect(self.guardar_perfil_usuario)
        self.btn_cargar_json.clicked.connect(self.cargar_perfil_usuario)
        self.btn_config_snap.clicked.connect(self.aplicar_snapping)

        self.btn_step1.clicked.connect(lambda: self.solicitar_ejecucion_paso.emit(1))
        self.btn_step2.clicked.connect(lambda: self.solicitar_ejecucion_paso.emit(2))
        self.btn_step3.clicked.connect(lambda: self.solicitar_ejecucion_paso.emit(3))
        self.btn_step4.clicked.connect(lambda: self.solicitar_ejecucion_paso.emit(4))
        self.btn_step5.clicked.connect(lambda: self.solicitar_ejecucion_paso.emit(5))
        self.btn_step6.clicked.connect(lambda: self.solicitar_ejecucion_paso.emit(6))
        self.btn_step7.clicked.connect(lambda: self.solicitar_ejecucion_paso.emit(7))
        self.btn_ejecutar_todo.clicked.connect(self.solicitar_ejecucion_completa.emit)
        self.btn_ayuda.clicked.connect(self.solicitar_ayuda.emit)

    def actualizar_clasificacion_ui(self):
        """Sincroniza simultáneamente los parámetros de la norma al cambiar entre Urbano y Rural."""
        es_urbano = self.rb_urbano.isChecked()
        p = obtener_parametros_norma('urbano' if es_urbano else 'rural')

        self.spn_dotacion.setValue(p['dotacion_gal_hab_dia'])
        self.lbl_presion_min.setText(f"{p['presion_min_psi']:.1f} psi ({p['presion_min_mca']:.2f} mca)")
        self.cmb_diam_troncal.setCurrentText(p['diam_min_troncal'])
        self.cmb_diam_ramal.setCurrentText(p['diam_min_ramal'])
        self.spn_fmh.setValue(p['factor_pico'])
        self.spn_prof_zanja.setValue(p['profundidad_zanja_m'])

        tipo_str = "URBANO (IDAAN: 100 gal, 20 psi, Troncal 4\")" if es_urbano else "RURAL (MINSA: 80 gal, 14 psi, Troncal 3\")"
        self.log_info(f"Clasificación actualizada: {tipo_str}")

    def on_cambio_perfil_combo(self, index):
        if index == 0:
            self.aplicar_perfil(obtener_perfil_predeterminado())
        elif index == 1:
            self.aplicar_perfil(dict(PERFIL_RURAL_MINSA))

    def aplicar_perfil(self, config):
        """Carga un diccionario de configuración en los controles de la UI."""
        clasif = config.get("clasificacion", "urbano").lower()
        if "rur" in clasif:
            self.rb_rural.setChecked(True)
        else:
            self.rb_urbano.setChecked(True)

        self.spn_dotacion.setValue(float(config.get("dotacion_gal_hab_dia", 100.0)))
        self.spn_offset.setValue(float(config.get("offset_tuberias_m", 5.0)))
        self.spn_prof_zanja.setValue(float(config.get("profundidad_zanja_m", 1.15)))
        self.spn_h_torre.setValue(float(config.get("altura_torre_tanque_m", 15.0)))
        self.spn_tolerancia_snap.setValue(float(config.get("tolerancia_snapping_m", 0.75)))
        self.spn_fmh.setValue(float(config.get("factor_pico_fmh", 2.00)))

        self.log_info(f"Perfil cargado: {config.get('nombre_perfil', 'Personalizado')}")

    def obtener_configuracion_actual(self):
        """Retorna un diccionario con los valores actuales fijados en la interfaz."""
        return {
            "nombre_perfil": self.cmb_perfil.currentText(),
            "clasificacion": "urbano" if self.rb_urbano.isChecked() else "rural",
            "dotacion_gal_hab_dia": self.spn_dotacion.value(),
            "offset_tuberias_m": self.spn_offset.value(),
            "profundidad_zanja_m": self.spn_prof_zanja.value(),
            "altura_torre_tanque_m": self.spn_h_torre.value(),
            "tolerancia_snapping_m": self.spn_tolerancia_snap.value(),
            "factor_pico_fmh": self.spn_fmh.value(),
            "diam_min_troncal": self.cmb_diam_troncal.currentText(),
            "diam_min_ramal": self.cmb_diam_ramal.currentText()
        }

    def guardar_perfil_usuario(self):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Perfil de Diseño", "", "Archivos JSON (*.json)")
        if path:
            cfg = self.obtener_configuracion_actual()
            guardar_perfil_a_archivo(cfg, path)
            self.log_info(f"Perfil guardado exitosamente en: {path}")
            QMessageBox.information(self, "AquaRed", f"Perfil guardado correctamente en:\n{path}")

    def cargar_perfil_usuario(self):
        path, _ = QFileDialog.getOpenFileName(self, "Cargar Perfil de Diseño", "", "Archivos JSON (*.json)")
        if path and os.path.exists(path):
            cfg = cargar_perfil_desde_archivo(path)
            self.aplicar_perfil(cfg)
            self.cmb_perfil.setCurrentText("Personalizado...")
            self.log_info(f"Perfil cargado desde: {path}")

    def aplicar_snapping(self):
        tol = self.spn_tolerancia_snap.value()
        SnappingManager.configurar_snapping_proyecto(tolerancia_m=tol)
        self.log_info(f"Auto-Snapping configurado a {tol:.2f} m con intersecciones y edición topológica activada.")
        QMessageBox.information(self, "AquaRed Snapping", f"Auto-snapping configurado a {tol:.2f} m (Vértice + Segmento + Intersecciones + Edición Topológica).")

    def log_info(self, mensaje):
        self.txt_log.append(f"• {mensaje}")
        self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())
