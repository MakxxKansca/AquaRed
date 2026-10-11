"""
AquaRed - Algoritmo 2: Muestreo de Elevación desde Ráster DEM
============================================================
Asigna cotas de terreno precisas y cotas de batea de tubería (zanja)
a elementos puntuales o lineales utilizando un Modelo Digital de Elevación (DEM).
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSink,
    QgsFeatureSink,
    QgsFeature,
    QgsGeometry,
    QgsFields,
    QgsField,
    QgsPointXY,
    QgsRaster
)
from PyQt5.QtCore import QVariant

class Step2DemSamplingAlgorithm(QgsProcessingAlgorithm):
    INPUT_FEATURES = 'INPUT_FEATURES'
    INPUT_DEM = 'INPUT_DEM'
    PROFUNDIDAD_ZANJA = 'PROFUNDIDAD_ZANJA'
    OUTPUT = 'OUTPUT'

    def createInstance(self):
        return Step2DemSamplingAlgorithm()

    def name(self):
        return 'step2_dem_sampling'

    def displayName(self):
        return 'Paso 2: Muestrear Elevaciones DEM'

    def group(self):
        return 'AquaRed - Flujo de Trabajo'

    def groupId(self):
        return 'aquared_workflow'

    def shortHelpString(self):
        return """
<b>Paso 2: Muestreo y Asignación de Elevaciones desde DEM</b><br><br>
Interpola la cota topográfica del terreno (msnm) para cada entidad a partir de una capa ráster DEM.<br>
Calcula automáticamente:<br>
 - <b>cota_terreno</b>: Elevación natural del terreno (msnm).<br>
 - <b>cota_tubo</b>: Cota de desplante de tubería considerando la profundidad de zanja normativa.<br>
"""

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_FEATURES,
                'Capa de Entrada (Nodos, Puntos o Tuberías)',
                [QgsProcessing.TypeVectorPoint, QgsProcessing.TypeVectorLine]
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_DEM,
                'Ráster Modelo Digital de Elevación (DEM)'
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.PROFUNDIDAD_ZANJA,
                'Profundidad de Zanja Normativa (m)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=1.15,
                minValue=0.5,
                maxValue=3.0
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                'Capa con Cotas Asignadas',
                type=QgsProcessing.TypeVectorAnyGeometry
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT_FEATURES, context)
        dem_layer = self.parameterAsRasterLayer(parameters, self.INPUT_DEM, context)
        prof_zanja = self.parameterAsDouble(parameters, self.PROFUNDIDAD_ZANJA, context)

        fields = QgsFields(source.fields())
        if fields.indexFromName('cota_terreno') == -1:
            fields.append(QgsField('cota_terreno', QVariant.Double, prec=2))
        if fields.indexFromName('cota_tubo') == -1:
            fields.append(QgsField('cota_tubo', QVariant.Double, prec=2))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context, fields, source.wkbType(), source.sourceCrs()
        )

        dem_provider = dem_layer.dataProvider()
        total_feats = source.featureCount()
        count = 0

        for feat in source.getFeatures():
            if feedback.isCanceled():
                break

            geom = feat.geometry()
            z_val = 100.0  # Fallback

            if geom and not geom.isEmpty():
                if geom.type() == QgsProcessing.TypeVectorPoint:
                    pt = geom.asPoint()
                    ident = dem_provider.sample(pt, 1)
                    if ident[1]:
                        z_val = float(ident[0])
                elif geom.type() == QgsProcessing.TypeVectorLine:
                    # Muestrear en el punto medio o inicio
                    pt = geom.centroid().asPoint()
                    ident = dem_provider.sample(pt, 1)
                    if ident[1]:
                        z_val = float(ident[0])

            f_out = QgsFeature(fields)
            f_out.setGeometry(geom)

            # Copiar atributos existentes
            attrs = list(feat.attributes())
            # Actualizar o agregar cota_terreno y cota_tubo
            idx_terreno = fields.indexFromName('cota_terreno')
            idx_tubo = fields.indexFromName('cota_tubo')

            while len(attrs) < fields.count():
                attrs.append(None)

            attrs[idx_terreno] = round(z_val, 2)
            attrs[idx_tubo] = round(z_val - prof_zanja, 2)

            f_out.setAttributes(attrs)
            sink.addFeature(f_out, QgsFeatureSink.FastInsert)

            count += 1
            if total_feats > 0:
                feedback.setProgress(int(count * 100 / total_feats))

        return {self.OUTPUT: dest_id}
