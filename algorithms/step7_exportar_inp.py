"""
AquaRed - Algoritmo 7: Exportación Nativa a EPANET (.INP)
========================================================
Construye y exporta el modelo hidráulico definitivo en formato ASCII estándar EPANET (.INP).
Totalmente autocontenido, sin dependencias externas como WNTR.
Incluye vértices de curvatura para trazado idéntico a QGIS, cotas piezométricas y [BACKDROP].
"""

import os
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFileDestination,
    QgsProcessingOutputString
)
from shapely import wkt
from ..core.epanet_exporter import EpanetExporter

class Step7ExportarInpAlgorithm(QgsProcessingAlgorithm):
    INPUT_TUBERIAS = 'INPUT_TUBERIAS'
    INPUT_NODOS = 'INPUT_NODOS'
    INPUT_TANQUE = 'INPUT_TANQUE'
    ALTURA_TORRE = 'ALTURA_TORRE'
    OUTPUT_INP = 'OUTPUT_INP'
    RESULT_SUMMARY = 'RESULT_SUMMARY'

    def createInstance(self):
        return Step7ExportarInpAlgorithm()

    def name(self):
        return 'step7_exportar_inp'

    def displayName(self):
        return 'Paso 7: Exportar Red a EPANET (.INP)'

    def group(self):
        return 'AquaRed - Flujo de Trabajo'

    def groupId(self):
        return 'aquared_workflow'

    def shortHelpString(self):
        return """
<b>Paso 7: Exportación Directa a EPANET (.INP) Autocontenida</b><br><br>
Genera un archivo .INP estándar compatible con EPANET 2.0 / 2.2 y herramientas GIS.<br>
<b>Características del archivo generado:</b><br>
 - <b>Unidades métricas (LPS)</b>: Diámetros en mm, longitudes en m y caudales en L/s.<br>
 - <b>Vértices de curvatura [VERTICES]</b>: Dibuja las tuberías con las curvas exactas de las calles.<br>
 - <b>Encuadre espacial [BACKDROP]</b>: Coordenadas y dimensiones coincidentes con el plano QGIS.<br>
 - <b>Patrón de modulación horaria [PATTERNS]</b>: Perfil de 24 horas normalizado con pico a las 06:00 AM.<br>
"""

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_TUBERIAS,
                'Capa de Tuberías Matrices',
                [QgsProcessing.TypeVectorLine]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_NODOS,
                'Capa de Nodos de Red (con Demandas Asignadas)',
                [QgsProcessing.TypeVectorPoint]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_TANQUE,
                'Capa de Tanque / Fuente de Alimentación',
                [QgsProcessing.TypeVectorPoint]
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ALTURA_TORRE,
                'Altura de Torre de Tanque Elevado (m)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=15.00,
                minValue=0.0,
                maxValue=50.0
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_INP,
                'Archivo EPANET de Salida (.INP)',
                fileFilter='EPANET Input Files (*.inp *.INP)'
            )
        )
        self.addOutput(
            QgsProcessingOutputString(
                self.RESULT_SUMMARY,
                'Resumen de Exportación'
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        tub_source = self.parameterAsSource(parameters, self.INPUT_TUBERIAS, context)
        nod_source = self.parameterAsSource(parameters, self.INPUT_NODOS, context)
        tanque_source = self.parameterAsSource(parameters, self.INPUT_TANQUE, context)
        h_torre = self.parameterAsDouble(parameters, self.ALTURA_TORRE, context)
        out_path = self.parameterAsFileOutput(parameters, self.OUTPUT_INP, context)

        exporter = EpanetExporter(title="AquaRed - Modelo Definitivo de Red Matriz")

        # 1. Tanque / Reservorio
        id_tanque = "TK-001"
        cota_agua_total = 115.0
        pt_tank = None

        for feat in tanque_source.getFeatures():
            id_tanque = str(feat.attribute('id_tanque') or feat.attribute('id') or "TK-001")
            cota_terreno_tanque = float(feat.attribute('cota_terreno') or feat.attribute('cota') or 100.0)
            cota_agua_total = cota_terreno_tanque + h_torre
            geom_t = feat.geometry()
            if geom_t and not geom_t.isEmpty():
                pt_tank = geom_t.asPoint()
            break

        if pt_tank:
            exporter.add_reservoir(id_tanque, total_head=cota_agua_total, x=pt_tank.x(), y=pt_tank.y())
        else:
            exporter.add_reservoir(id_tanque, total_head=cota_agua_total)

        feedback.pushInfo(f"Reservorio '{id_tanque}' configurado con Cota Piezométrica = {cota_agua_total:.2f} msnm")

        # 2. Nodos Matrices
        nodos_count = 0
        for feat in nod_source.getFeatures():
            nid = str(feat.attribute('id_nodo') or feat.attribute('id'))
            if nid == id_tanque:
                continue

            elev = float(feat.attribute('cota_terreno') or feat.attribute('cota') or 100.0)
            dem_lps = float(feat.attribute('demanda_diseno_lps') or feat.attribute('demanda_lps') or 0.0)

            geom_n = feat.geometry()
            pt_n = geom_n.asPoint() if geom_n and not geom_n.isEmpty() else None

            exporter.add_junction(
                node_id=nid,
                elevation=elev,
                demand_lps=dem_lps,
                pattern="PATRON_HORARIO",
                x=pt_n.x() if pt_n else None,
                y=pt_n.y() if pt_n else None
            )
            nodos_count += 1

        # 3. Tuberías Matrices con vértices
        pipes_count = 0
        for feat in tub_source.getFeatures():
            pid = str(feat.attribute('id_tubo') or feat.attribute('id'))
            na = str(feat.attribute('nodo_ini'))
            nb = str(feat.attribute('nodo_fin'))
            l_m = float(feat.attribute('longitud_m') or feat.geometry().length() or 10.0)
            d_mm = float(feat.attribute('diam_int_mm') or 82.1)
            c_hw = float(feat.attribute('c_hazen') or 140.0)

            # Vértices intermedios
            vertices = []
            geom_p = feat.geometry()
            if geom_p and not geom_p.isEmpty():
                s_geom = wkt.loads(geom_p.asWkt())
                coords = list(s_geom.coords)
                if len(coords) > 2:
                    vertices = [(round(cx, 3), round(cy, 3)) for cx, cy in coords[1:-1]]

            exporter.add_pipe(
                pipe_id=pid,
                node1=na,
                node2=nb,
                length_m=l_m,
                diameter_mm=d_mm,
                roughness=c_hw,
                vertices=vertices
            )
            pipes_count += 1

        # Exportar
        feedback.pushInfo(f"Escribiendo archivo EPANET a: {out_path}...")
        exporter.export_inp(out_path)

        res_msg = f"Exportación exitosa a EPANET (.INP): {nodos_count} Nodos, 1 Tanque, {pipes_count} Tuberías Matrices."
        feedback.pushInfo(f" >>> {res_msg}")

        return {
            self.OUTPUT_INP: out_path,
            self.RESULT_SUMMARY: res_msg
        }
