"""
AquaRed - Algoritmo 4: Trazado de Acometidas Domiciliarias
=========================================================
Conecta cada vivienda de forma perpendicular a la tubería matriz más cercana.
Genera la capa de líneas de acometida (1/2") y la capa de puntos de toma de derivación.
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
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
from shapely.geometry import Point, LineString
from ..core.topology_engine import trazar_acometidas

class Step4AcometidasAlgorithm(QgsProcessingAlgorithm):
    INPUT_TUBERIAS = 'INPUT_TUBERIAS'
    INPUT_CASAS = 'INPUT_CASAS'
    UMBRAL_MAX_DIST = 'UMBRAL_MAX_DIST'
    OUTPUT_ACOMETIDAS = 'OUTPUT_ACOMETIDAS'
    OUTPUT_TOMAS = 'OUTPUT_TOMAS'

    def createInstance(self):
        return Step4AcometidasAlgorithm()

    def name(self):
        return 'step4_acometidas'

    def displayName(self):
        return 'Paso 4: Trazar Acometidas Domiciliarias'

    def group(self):
        return 'AquaRed - Flujo de Trabajo'

    def groupId(self):
        return 'aquared_workflow'

    def shortHelpString(self):
        return """
<b>Paso 4: Trazado Perpendicular de Acometidas Domiciliarias</b><br><br>
Traza la conexión hidráulica desde el centroide de cada vivienda hasta el punto perpendicular
más cercano sobre la red de tuberías matrices.<br>
<b>Salidas generadas:</b><br>
 - <b>Acometidas</b>: Líneas de polietileno/PVC Ø 1/2" asociadas a su vivienda y a su tramo de tubería matriz.<br>
 - <b>Tomas de derivación</b>: Puntos sobre la tubería donde se inserta la abrazadera de conexión.<br>
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
                self.INPUT_CASAS,
                'Capa de Viviendas / Edificaciones',
                [QgsProcessing.TypeVectorPoint, QgsProcessing.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.UMBRAL_MAX_DIST,
                'Distancia Máxima de Conexión Admisible (m)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=40.0,
                minValue=5.0,
                maxValue=200.0
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_ACOMETIDAS,
                'Acometidas Domiciliarias (Líneas 1/2")',
                type=QgsProcessing.TypeVectorLine
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_TOMAS,
                'Puntos de Toma en Tubería (Puntos)',
                type=QgsProcessing.TypeVectorPoint
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        tub_source = self.parameterAsSource(parameters, self.INPUT_TUBERIAS, context)
        casas_source = self.parameterAsSource(parameters, self.INPUT_CASAS, context)
        umbral_m = self.parameterAsDouble(parameters, self.UMBRAL_MAX_DIST, context)
        crs = tub_source.sourceCrs()

        # Extraer tuberías a formato Shapely
        pipes_list = []
        for feat in tub_source.getFeatures():
            g = feat.geometry()
            if g and not g.isEmpty():
                geom_s = wkt.loads(g.asWkt())
                tid = feat.attribute('id_tubo') or feat.attribute('id') or f"T-{len(pipes_list)+1:03d}"
                pipes_list.append({
                    'id_tubo': str(tid),
                    'geometry': geom_s
                })

        # Extraer casas a formato Shapely
        casas_list = []
        for feat in casas_source.getFeatures():
            g = feat.geometry()
            if g and not g.isEmpty():
                geom_s = wkt.loads(g.asWkt())
                cid = feat.attribute('id_casa') or feat.attribute('id') or f"CASA-{len(casas_list)+1:03d}"
                casas_list.append({
                    'id_casa': str(cid),
                    'geometry': geom_s
                })

        feedback.pushInfo(f"Calculando trazado de acometidas para {len(casas_list)} viviendas...")
        acometidas, tomas = trazar_acometidas(casas_list, pipes_list, umbral_max_m=umbral_m)

        # Campos Acometidas
        fields_ac = QgsFields()
        fields_ac.append(QgsField('id_acometida', QVariant.String, len=50))
        fields_ac.append(QgsField('id_casa', QVariant.String, len=50))
        fields_ac.append(QgsField('id_tubo_matriz', QVariant.String, len=50))
        fields_ac.append(QgsField('longitud_m', QVariant.Double, prec=2))
        fields_ac.append(QgsField('diam_pulg', QVariant.Double, prec=2))
        fields_ac.append(QgsField('material', QVariant.String, len=50))
        fields_ac.append(QgsField('tipo_acometida', QVariant.String, len=50))

        (sink_ac, dest_id_ac) = self.parameterAsSink(
            parameters, self.OUTPUT_ACOMETIDAS, context, fields_ac, QgsWkbTypes.LineString, crs
        )

        # Campos Tomas
        fields_toma = QgsFields()
        fields_toma.append(QgsField('id_toma', QVariant.String, len=50))
        fields_toma.append(QgsField('id_acometida', QVariant.String, len=50))
        fields_toma.append(QgsField('id_casa', QVariant.String, len=50))
        fields_toma.append(QgsField('id_tubo_matriz', QVariant.String, len=50))

        (sink_toma, dest_id_toma) = self.parameterAsSink(
            parameters, self.OUTPUT_TOMAS, context, fields_toma, QgsWkbTypes.Point, crs
        )

        for ac in acometidas:
            f = QgsFeature(fields_ac)
            f.setGeometry(QgsGeometry.fromWkt(ac['geometry'].wkt))
            f.setAttributes([
                ac['id_acometida'], ac['id_casa'], ac['id_tubo_matriz'],
                ac['longitud_m'], ac['diam_pulg'], ac['material'], ac['tipo_acometida']
            ])
            sink_ac.addFeature(f, QgsFeatureSink.FastInsert)

        for t in tomas:
            f = QgsFeature(fields_toma)
            pt = t['geometry']
            f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x, pt.y)))
            f.setAttributes([
                t['id_toma'], t['id_acometida'], t['id_casa'], t['id_tubo_matriz']
            ])
            sink_toma.addFeature(f, QgsFeatureSink.FastInsert)

        feedback.pushInfo(f"Se generaron {len(acometidas)} acometidas domiciliarias conectadas a la red.")

        return {
            self.OUTPUT_ACOMETIDAS: dest_id_ac,
            self.OUTPUT_TOMAS: dest_id_toma
        }
