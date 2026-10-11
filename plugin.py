"""
AquaRed - Clase Principal del Plugin QGIS
=========================================
Controla el ciclo de vida del complemento (initGui / unload),
registra el Processing Provider, añade las acciones a la barra de herramientas
y administra el panel acoplable (DockWidget) y el diálogo de ayuda técnica.
"""

import os
from PyQt5.QtWidgets import QAction, QMessageBox, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsProcessingContext,
    QgsProcessingFeedback
)
import processing

from .algorithms.provider import AquaRedProvider
from .gui.dockwidget import AquaRedDockWidget
from .help.help_dialog import AquaRedHelpDialog
from .core.idaan_rules import obtener_parametros_norma
from .core.epanet_exporter import EpanetExporter

class AquaRedPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.dock_widget = None
        self.action = None
        self.menu_name = "&AquaRed"

    def initProcessing(self):
        self.provider = AquaRedProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

        # Icono principal
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        # Acción en barra de herramientas
        self.action = QAction(icon, "AquaRed - Diseñador de Redes de Agua Potable", self.iface.mainWindow())
        self.action.triggered.connect(self.toggle_dock_widget)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.menu_name, self.action)

        # Crear y añadir DockWidget
        self.dock_widget = AquaRedDockWidget(self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        self.dock_widget.hide()

        # Conectar señales del DockWidget
        self.dock_widget.solicitar_ejecucion_paso.connect(self.ejecutar_paso_procesamiento)
        self.dock_widget.solicitar_ejecucion_completa.connect(self.ejecutar_flujo_completo)
        self.dock_widget.solicitar_ayuda.connect(self.mostrar_ayuda)

    def unload(self):
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)

        if self.action:
            self.iface.removePluginMenu(self.menu_name, self.action)
            self.iface.removeToolBarIcon(self.action)

        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()

    def toggle_dock_widget(self):
        if self.dock_widget:
            if self.dock_widget.isVisible():
                self.dock_widget.hide()
            else:
                self.dock_widget.show()
                self.dock_widget.raise_()

    def mostrar_ayuda(self):
        dialog = AquaRedHelpDialog(self.iface.mainWindow())
        dialog.exec_()

    def ejecutar_paso_procesamiento(self, paso_num):
        """Abre el diálogo del algoritmo de Processing correspondiente al paso."""
        alg_map = {
            1: 'aquared:step1_extraer_base',
            2: 'aquared:step2_dem_sampling',
            3: 'aquared:step3_trazar_offset',
            4: 'aquared:step4_acometidas',
            5: 'aquared:step5_demandas_idaan',
            6: 'aquared:step6_validaciones',
            7: 'aquared:step7_exportar_inp'
        }
        alg_id = alg_map.get(paso_num)
        if alg_id:
            try:
                processing.execAlgorithmDialog(alg_id)
            except Exception as e:
                QMessageBox.warning(self.iface.mainWindow(), "AquaRed", f"Error al abrir algoritmo {alg_id}:\n{str(e)}")

    def ejecutar_flujo_completo(self):
        """Ejecuta el flujo completo automatizado con los parámetros configurados en el panel."""
        self.dock_widget.log_info("═══════════════════════════════════════════════════════════")
        self.dock_widget.log_info("INICIANDO FLUJO COMPLETO AUTOMATIZADO DE DISEÑO HIDRÁULICO")
        self.dock_widget.log_info("═══════════════════════════════════════════════════════════")

        cfg = self.dock_widget.obtener_configuracion_actual()
        self.dock_widget.log_info(f"Modo seleccionado: {cfg['clasificacion'].upper()} | Dotación: {cfg['dotacion_gal_hab_dia']} gal/hab/día")
        self.dock_widget.log_info(f"Offset vial configurado: {cfg['offset_tuberias_m']} m | Zanja: {cfg['profundidad_zanja_m']} m")

        # Verificar capas mínimas
        layer_vias = self.dock_widget.cmb_layer_calles.currentLayer()
        layer_casas = self.dock_widget.cmb_layer_casas.currentLayer()

        if not layer_vias or not layer_casas:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "AquaRed - Flujo Completo",
                "Para ejecutar el flujo completo debe seleccionar al menos una capa de Calles y una capa de Viviendas en el panel."
            )
            return

        try:
            # Paso 3: Trazado de tuberías con offset
            self.dock_widget.log_info("Ejecutando Paso 3: Trazado de Tuberías con Offset...")
            res_p3 = processing.run("aquared:step3_trazar_offset", {
                'INPUT_VIAS': layer_vias,
                'OFFSET_DISTANCIA': cfg['offset_tuberias_m'],
                'CLASIFICACION': 0 if cfg['clasificacion'] == 'urbano' else 1,
                'OUTPUT_TUBERIAS': 'TEMPORARY_OUTPUT',
                'OUTPUT_NODOS': 'TEMPORARY_OUTPUT'
            })
            tub_layer = res_p3['OUTPUT_TUBERIAS']
            nod_layer = res_p3['OUTPUT_NODOS']
            tub_layer.setName("Tuberías Matrices (Offset 5m)")
            nod_layer.setName("Nodos de Red")
            QgsProject.instance().addMapLayer(tub_layer)
            QgsProject.instance().addMapLayer(nod_layer)
            self.dock_widget.log_info(f"Tuberías generadas: {tub_layer.featureCount()} tramos | Nodos: {nod_layer.featureCount()}")

            # Paso 4: Acometidas
            self.dock_widget.log_info("Ejecutando Paso 4: Trazado de Acometidas...")
            res_p4 = processing.run("aquared:step4_acometidas", {
                'INPUT_TUBERIAS': tub_layer,
                'INPUT_CASAS': layer_casas,
                'UMBRAL_MAX_DIST': 50.0,
                'OUTPUT_ACOMETIDAS': 'TEMPORARY_OUTPUT',
                'OUTPUT_TOMAS': 'TEMPORARY_OUTPUT'
            })
            ac_layer = res_p4['OUTPUT_ACOMETIDAS']
            ac_layer.setName("Acometidas Domiciliarias (1/2\")")
            QgsProject.instance().addMapLayer(ac_layer)
            self.dock_widget.log_info(f"Acometidas generadas: {ac_layer.featureCount()} viviendas conectadas.")

            # Paso 5: Asignación de Demandas (Método Tramo IDAAN)
            self.dock_widget.log_info("Ejecutando Paso 5: Asignación de Demandas (Método Tramo IDAAN)...")
            res_p5 = processing.run("aquared:step5_demandas_idaan", {
                'INPUT_TUBERIAS': tub_layer,
                'INPUT_ACOMETIDAS': ac_layer,
                'INPUT_NODOS': nod_layer,
                'CLASIFICACION': 0 if cfg['clasificacion'] == 'urbano' else 1,
                'DOTACION': cfg['dotacion_gal_hab_dia'],
                'HAB_POR_CASA': 5.0,
                'FACTOR_PICO': cfg['factor_pico_fmh'],
                'OUTPUT_NODOS_DEMANDA': 'TEMPORARY_OUTPUT'
            })
            nod_dem_layer = res_p5['OUTPUT_NODOS_DEMANDA']
            nod_dem_layer.setName("Nodos de Red con Demandas IDAAN")
            QgsProject.instance().addMapLayer(nod_dem_layer)

            # Paso 6: Validaciones y Válvulas
            self.dock_widget.log_info("Ejecutando Paso 6: Validación Topológica y Válvulas...")
            res_p6 = processing.run("aquared:step6_validaciones", {
                'INPUT_TUBERIAS': tub_layer,
                'INPUT_NODOS': nod_dem_layer,
                'ID_FUENTE': 'TK-001',
                'OUTPUT_VALVULAS': 'TEMPORARY_OUTPUT'
            })
            valv_layer = res_p6['OUTPUT_VALVULAS']
            valv_layer.setName("Válvulas y Accesorios Propuestos")
            QgsProject.instance().addMapLayer(valv_layer)

            # Paso 7: Preguntar si desea exportar INP
            save_inp_path, _ = QFileDialog.getSaveFileName(
                self.iface.mainWindow(),
                "Exportar Red a EPANET (.INP)",
                "red_agua_potable.inp",
                "EPANET Model (*.inp)"
            )
            if save_inp_path:
                layer_tanque = self.dock_widget.cmb_layer_tanque.currentLayer()
                if layer_tanque:
                    processing.run("aquared:step7_exportar_inp", {
                        'INPUT_TUBERIAS': tub_layer,
                        'INPUT_NODOS': nod_dem_layer,
                        'INPUT_TANQUE': layer_tanque,
                        'ALTURA_TORRE': cfg['altura_torre_tanque_m'],
                        'OUTPUT_INP': save_inp_path
                    })
                    self.dock_widget.log_info(f"Modelo EPANET exportado exitosamente a: {save_inp_path}")

            self.dock_widget.log_info(">>> FLUJO COMPLETO FINALIZADO CON ÉXITO ROTUNDO <<<")
            QMessageBox.information(self.iface.mainWindow(), "AquaRed", "Flujo completo de diseño hidráulico ejecutado con éxito.\nTodas las capas han sido cargadas en el mapa.")

        except Exception as e:
            self.dock_widget.log_info(f"[ERROR]: Falló la ejecución del flujo: {str(e)}")
            QMessageBox.critical(self.iface.mainWindow(), "AquaRed - Error", f"Ocurrió un error durante la ejecución:\n{str(e)}")
