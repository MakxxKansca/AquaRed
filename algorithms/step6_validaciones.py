"""
AquaRed - Algoritmo 6: Validación Topológica y Generación de Válvulas
====================================================================
Valida la conectividad hidráulica de la red de tuberías (grafo conexo único),
detecta extremos terminales y genera automáticamente las válvulas técnicas normativas:
 - Compuerta de aislamiento maestro en aducción.
 - Ventosa trifuncional de aire en el punto alto.
 - Válvulas de compuerta en cabeceras de ramales secundarios (Tees).
 - Válvulas de purga y desagüe en fondos de saco terminales.
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterString,
    QgsProcessingParameterFeatureSink,
    QgsFeatureSink,
    QgsFeature,
    QgsGeometry,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsPointXY
)
from PyQt5.QtCore import QVariant
from shapely import wkt
from ..core.topology_engine import validar_topologia_red, generar_valvulas_tecnicas

class Step6ValidacionesAlgorithm(QgsProcessingAlgorithm):
    INPUT_TUBERIAS = 'INPUT_TUBERIAS'
    INPUT_NODOS = 'INPUT_NODOS'
    ID_FUENTE = 'ID_FUENTE'
    OUTPUT_VALVULAS = 'OUTPUT_VALVULAS'

    def createInstance(self):
        return Step6ValidacionesAlgorithm()

    def name(self):
        return 'step6_validaciones'

    def displayName(self):
        return 'Paso 6: Validar Topología y Generar Válvulas'

    def group(self):
        return 'AquaRed - Flujo de Trabajo'

    def groupId(self):
        return 'aquared_workflow'

    def shortHelpString(self):
        return """
<b>Paso 6: Validación de Conectividad Topológica y Accesorios Técnicos</b><br><br>
Examina el grafo de la red garantizando que no existan tramos aislados o desbalanceados.<br>
<b>Accesorios y Válvulas Generadas:</b><br>
 - <b>Aislamiento Maestro</b>: Válvula de compuerta sobre la línea de alimentación/aducción.<br>
 - <b>Punto Alto</b>: Ventosa trifuncional para purga automática de bolsas de aire.<br>
 - <b>Seccionamiento</b>: Compuertas en la cabecera de cada ramal transversal.<br>
 - <b>Fondos de Saco</b>: Válvulas de purga y desagüe para mantenimiento en terminales.<br>
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
                'Capa de Nodos de Red',
                [QgsProcessing.TypeVectorPoint]
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.ID_FUENTE,
                'ID del Nodo Tanque / Fuente',
                defaultValue='TK-001'
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_VALVULAS,
                'Válvulas y Accesorios Técnicos Propuestos',
                type=QgsProcessing.TypeVectorPoint
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        tub_source = self.parameterAsSource(parameters, self.INPUT_TUBERIAS, context)
        nod_source = self.parameterAsSource(parameters, self.INPUT_NODOS, context)
        id_fuente = self.parameterAsString(parameters, self.ID_FUENTE, context)
        crs = nod_source.sourceCrs()

        pipes_list = []
        for feat in tub_source.getFeatures():
            tid = feat.attribute('id_tubo') or feat.attribute('id')
            na = feat.attribute('nodo_ini')
            nb = feat.attribute('nodo_fin')
            nom = feat.attribute('calle') or ""
            dpulg = feat.attribute('diam_nom_pulg') or 3.0
            geom_q = feat.geometry()
            geom_s = wkt.loads(geom_q.asWkt()) if geom_q else None
            pipes_list.append({
                'id_tubo': str(tid),
                'nodo_ini': str(na),
                'nodo_fin': str(nb),
                'calle': str(nom),
                'diam_nom_pulg': float(dpulg),
                'geometry': geom_s
            })

        nodos_list = []
        for feat in nod_source.getFeatures():
            nid = feat.attribute('id_nodo') or feat.attribute('id')
            nom = feat.attribute('nombre') or str(nid)
            cota = feat.attribute('cota_terreno') or 100.0
            geom_q = feat.geometry()
            geom_s = wkt.loads(geom_q.asWkt()) if geom_q else None
            nodos_list.append({
                'id_nodo': str(nid),
                'nombre': str(nom),
                'cota_terreno': float(cota),
                'geometry': geom_s
            })

        # 1. Validación Topológica
        feedback.pushInfo("Ejecutando diagnóstico de conectividad topológica...")
        diag = validar_topologia_red(nodos_list, pipes_list, id_fuente=id_fuente)

        feedback.pushInfo("═══════════════════════════════════════════════════════════")
        feedback.pushInfo("DIAGNÓSTICO TOPOLÓGICO DE LA RED")
        feedback.pushInfo(f" • Total de Nodos en Grafo:       {diag['total_nodos']}")
        feedback.pushInfo(f" • Total de Tramos en Grafo:      {diag['total_tramos']}")
        feedback.pushInfo(f" • Componentes Conexos:           {diag['num_componentes']} ({'100% CONEXA' if diag['num_componentes'] == 1 else 'DESCONECTADA'})")
        feedback.pushInfo(f" • Nodos Terminales (Fondos Saco): {len(diag['terminales'])} -> {', '.join(diag['terminales'])}")

        if diag['errores']:
            for err in diag['errores']:
                feedback.reportError(f" [ERROR] {err}")
        else:
            feedback.pushInfo(" >>> VALIDACIÓN TOPOLÓGICA 100% EXITOSA (CERO ERRORES DE CONECTIVIDAD)")
        feedback.pushInfo("═══════════════════════════════════════════════════════════")

        # 2. Generación de Válvulas
        feedback.pushInfo("Generando accesorios técnicos y válvulas...")
        valvulas = generar_valvulas_tecnicas(pipes_list, nodos_list, id_fuente=id_fuente)

        fields_valv = QgsFields()
        fields_valv.append(QgsField('id_valvula', QVariant.String, len=50))
        fields_valv.append(QgsField('tipo', QVariant.String, len=100))
        fields_valv.append(QgsField('nodo_asociado', QVariant.String, len=50))
        fields_valv.append(QgsField('funcion', QVariant.String, len=200))
        fields_valv.append(QgsField('cota', QVariant.Double, prec=2))

        (sink_valv, dest_id_valv) = self.parameterAsSink(
            parameters, self.OUTPUT_VALVULAS, context, fields_valv, QgsWkbTypes.Point, crs
        )

        for v in valvulas:
            pt = v['geometry']
            if pt:
                f = QgsFeature(fields_valv)
                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x, pt.y)))
                f.setAttributes([
                    v['id_valvula'], v['tipo'], v['nodo_asociado'], v['funcion'], round(v.get('cota', 100.0), 2)
                ])
                sink_valv.addFeature(f, QgsFeatureSink.FastInsert)

        feedback.pushInfo(f"Se generaron {len(valvulas)} accesorios técnicos y válvulas de seccionamiento.")

        return {self.OUTPUT_VALVULAS: dest_id_valv}
