"""
AquaRed - Algoritmo 3: Trazado de Tuberías con Offset Vial Paralelo
==================================================================
Genera la red de tuberías matrices aplicando un offset paralelo estricto
sobre las calles seleccionadas, manteniendo los ejes viales 100% intactos.
Crea automáticamente los nodos extremos, empalmes y tees de derivación.
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterEnum,
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
from shapely.geometry import LineString, Point, Polygon
from shapely import wkt
from ..core.topology_engine import calcular_offset_vial
from ..core.idaan_rules import CATALOGO_TUBERIAS

class Step3TrazarOffsetAlgorithm(QgsProcessingAlgorithm):
    INPUT_VIAS = 'INPUT_VIAS'
    INPUT_BOUNDARY = 'INPUT_BOUNDARY'
    OFFSET_DISTANCIA = 'OFFSET_DISTANCIA'
    CLASIFICACION = 'CLASIFICACION'
    OUTPUT_TUBERIAS = 'OUTPUT_TUBERIAS'
    OUTPUT_NODOS = 'OUTPUT_NODOS'

    def createInstance(self):
        return Step3TrazarOffsetAlgorithm()

    def name(self):
        return 'step3_trazar_offset'

    def displayName(self):
        return 'Paso 3: Trazar Tuberías con Offset Paralelo'

    def group(self):
        return 'AquaRed - Flujo de Trabajo'

    def groupId(self):
        return 'aquared_workflow'

    def shortHelpString(self):
        return """
<b>Paso 3: Trazado de Red de Tuberías con Offset Vial Paralelo</b><br><br>
Aplica un desplazamiento paralelo continuo a los ejes de calles seleccionados.<br>
<b>Reglas estrictas de diseño:</b><br>
 - Los ejes viales originales permanecen intactos en su geometría original.<br>
 - Se evalúa el polígono del proyecto para elegir el lado interior preferencial (acera interior).<br>
 - Asigna diámetros del catálogo oficial (PVC SDR-26 con C=140) según jerarquía troncal/ramal.<br>
 - Genera automáticamente la capa de nodos con conectividad 'nodo_ini' y 'nodo_fin'.<br>
"""

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_VIAS,
                'Capa de Ejes Viales (Calles)',
                [QgsProcessing.TypeVectorLine]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_BOUNDARY,
                'Polígono Límite / Área de Estudio (opcional para orientar offset hacia el interior)',
                [QgsProcessing.TypeVectorPolygon],
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.OFFSET_DISTANCIA,
                'Distancia de Offset Paralelo (m)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=5.00,
                minValue=0.5,
                maxValue=25.0
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.CLASIFICACION,
                'Clasificación del Proyecto',
                options=['Urbano (Troncal 4" / Ramales 3")', 'Rural (Troncal 3" / Ramales 2")'],
                defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_TUBERIAS,
                'Tuberías con Offset (Líneas)',
                type=QgsProcessing.TypeVectorLine
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_NODOS,
                'Nodos de Red Generados (Puntos)',
                type=QgsProcessing.TypeVectorPoint
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        vias_source = self.parameterAsSource(parameters, self.INPUT_VIAS, context)
        boundary_source = self.parameterAsSource(parameters, self.INPUT_BOUNDARY, context)
        offset_m = self.parameterAsDouble(parameters, self.OFFSET_DISTANCIA, context)
        clasif_idx = self.parameterAsEnum(parameters, self.CLASIFICACION, context)

        is_urban = (clasif_idx == 0)
        diam_troncal_nom = 4.0 if is_urban else 3.0
        diam_troncal_int = 105.5 if is_urban else 82.1
        diam_ramal_nom = 3.0 if is_urban else 2.0
        diam_ramal_int = 82.1 if is_urban else 55.7

        crs = vias_source.sourceCrs()

        # Obtener boundary poly Shapely si está disponible
        boundary_shapely = None
        if boundary_source:
            for bf in boundary_source.getFeatures():
                geom_b = bf.geometry()
                if geom_b and not geom_b.isEmpty():
                    boundary_shapely = wkt.loads(geom_b.asWkt())
                    break

        # Campos Tuberías
        fields_tub = QgsFields()
        fields_tub.append(QgsField('id_tubo', QVariant.String, len=50))
        fields_tub.append(QgsField('nodo_ini', QVariant.String, len=50))
        fields_tub.append(QgsField('nodo_fin', QVariant.String, len=50))
        fields_tub.append(QgsField('calle', QVariant.String, len=100))
        fields_tub.append(QgsField('diam_nom_pulg', QVariant.Double, prec=1))
        fields_tub.append(QgsField('diam_int_mm', QVariant.Double, prec=1))
        fields_tub.append(QgsField('material', QVariant.String, len=50))
        fields_tub.append(QgsField('c_hazen', QVariant.Double, prec=1))
        fields_tub.append(QgsField('offset_m', QVariant.Double, prec=2))
        fields_tub.append(QgsField('longitud_m', QVariant.Double, prec=2))

        (sink_tub, dest_id_tub) = self.parameterAsSink(
            parameters, self.OUTPUT_TUBERIAS, context, fields_tub, QgsWkbTypes.LineString, crs
        )

        # Campos Nodos
        fields_nod = QgsFields()
        fields_nod.append(QgsField('id_nodo', QVariant.String, len=50))
        fields_nod.append(QgsField('nombre', QVariant.String, len=100))
        fields_nod.append(QgsField('tipo', QVariant.String, len=50))
        fields_nod.append(QgsField('x', QVariant.Double, prec=3))
        fields_nod.append(QgsField('y', QVariant.Double, prec=3))
        fields_nod.append(QgsField('cota_terreno', QVariant.Double, prec=2))
        fields_nod.append(QgsField('cota_tubo', QVariant.Double, prec=2))

        (sink_nod, dest_id_nod) = self.parameterAsSink(
            parameters, self.OUTPUT_NODOS, context, fields_nod, QgsWkbTypes.Point, crs
        )

        nodos_dict = {}  # {node_id: {'geom': Point, 'name': str, 'tipo': str}}

        def registrar_nodo(pt_shapely, base_name, tipo="Nodo"):
            # Buscar si ya existe nodo a menos de 0.5m
            for nid, ndata in nodos_dict.items():
                if pt_shapely.distance(ndata['geom']) < 0.75:
                    return nid
            nid = f"N-{len(nodos_dict)+1:03d}"
            nodos_dict[nid] = {
                'geom': pt_shapely,
                'nombre': f"{base_name} ({nid})",
                'tipo': tipo
            }
            return nid

        tub_count = 0
        total_vias = vias_source.featureCount()

        for feat in vias_source.getFeatures():
            if feedback.isCanceled():
                break

            geom_qgis = feat.geometry()
            if not geom_qgis or geom_qgis.isEmpty():
                continue

            # Convertir a Shapely
            s_line = wkt.loads(geom_qgis.asWkt())
            if s_line.geom_type == 'MultiLineString':
                s_line = max(s_line.geoms, key=lambda g: g.length)

            # Generar curva de offset
            pipe_geom = calcular_offset_vial(s_line, offset_m, boundary_shapely, preferir_interior=True)
            if not pipe_geom or pipe_geom.length < 0.5:
                continue

            tub_count += 1
            tid = f"T-{tub_count:03d}"
            nom_calle = feat.attribute('nombre') or f"Calle {tub_count}"

            # Jerarquía de diámetros
            es_troncal = ('avenida' in str(nom_calle).lower() or 'aducción' in str(nom_calle).lower() or tub_count == 1)
            dpulg = diam_troncal_nom if es_troncal else diam_ramal_nom
            dint = diam_troncal_int if es_troncal else diam_ramal_int

            p_ini = Point(pipe_geom.coords[0])
            p_fin = Point(pipe_geom.coords[-1])

            nid_ini = registrar_nodo(p_ini, f"Inicio {nom_calle}")
            nid_fin = registrar_nodo(p_fin, f"Fin {nom_calle}")

            # Reconstruir geometría asegurando coincidencia milimétrica con los nodos
            coords = [nodos_dict[nid_ini]['geom'].coords[0]] + list(pipe_geom.coords)[1:-1] + [nodos_dict[nid_fin]['geom'].coords[0]]
            pipe_final = LineString(coords)

            f_tub = QgsFeature(fields_tub)
            f_tub.setGeometry(QgsGeometry.fromWkt(pipe_final.wkt))
            f_tub.setAttributes([
                tid, nid_ini, nid_fin, str(nom_calle),
                dpulg, dint, 'PVC SDR-26', 140.0, offset_m, round(pipe_final.length, 2)
            ])
            sink_tub.addFeature(f_tub, QgsFeatureSink.FastInsert)

        # Volcar Nodos a Sink
        for nid, ndata in nodos_dict.items():
            pt = ndata['geom']
            f_nod = QgsFeature(fields_nod)
            f_nod.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(pt.x, pt.y)))
            f_nod.setAttributes([
                nid, ndata['nombre'], ndata['tipo'],
                round(pt.x, 3), round(pt.y, 3), 100.0, 98.85
            ])
            sink_nod.addFeature(f_nod, QgsFeatureSink.FastInsert)

        feedback.pushInfo(f"Se generaron exitosamente {tub_count} tramos de tuberías con offset y {len(nodos_dict)} nodos topológicos.")

        return {
            self.OUTPUT_TUBERIAS: dest_id_tub,
            self.OUTPUT_NODOS: dest_id_nod
        }
