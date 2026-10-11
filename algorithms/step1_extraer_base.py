"""
AquaRed - Algoritmo 1: Extracción de Calles y Edificaciones Base
==============================================================
Extrae la red vial y huellas/puntos de viviendas a partir de OpenStreetMap
o filtrando y preparando capas vectoriales existentes dentro del área de estudio.
"""

import json
import urllib.request
import urllib.parse
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterEnum,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterFeatureSink,
    QgsFeatureSink,
    QgsFeature,
    QgsGeometry,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsPointXY,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsProject
)
from PyQt5.QtCore import QVariant

class Step1ExtraerBaseAlgorithm(QgsProcessingAlgorithm):
    INPUT_BOUNDARY = 'INPUT_BOUNDARY'
    STREETS_MODE = 'STREETS_MODE'
    STREETS_LAYER = 'STREETS_LAYER'
    BUILDINGS_MODE = 'BUILDINGS_MODE'
    BUILDINGS_LAYER = 'BUILDINGS_LAYER'
    OUTPUT_VIAS = 'OUTPUT_VIAS'
    OUTPUT_CASAS = 'OUTPUT_CASAS'

    def createInstance(self):
        return Step1ExtraerBaseAlgorithm()

    def name(self):
        return 'step1_extraer_base'

    def displayName(self):
        return 'Paso 1: Extraer Calles y Viviendas'

    def group(self):
        return 'AquaRed - Flujo de Trabajo'

    def groupId(self):
        return 'aquared_workflow'

    def shortHelpString(self):
        return """
<b>Paso 1: Extracción y Preparación de Calles y Viviendas</b><br><br>
Prepara la información base del proyecto acotada por el polígono del área de estudio.
Permite descargar automáticamente desde OpenStreetMap (Overpass API) o seleccionar capas ya existentes en el proyecto.
Las viviendas se normalizan como puntos (centroides) con ID secuencial y atributos geométricos.
"""

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_BOUNDARY,
                'Polígono de Límite / Área de Estudio',
                [QgsProcessing.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.STREETS_MODE,
                'Origen de Calles',
                options=['Descargar de OpenStreetMap (Overpass API)', 'Usar Capa Vectorial Existente'],
                defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.STREETS_LAYER,
                'Capa de Calles Existente (si seleccionó usar capa)',
                types=[QgsProcessing.TypeVectorLine],
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.BUILDINGS_MODE,
                'Origen de Viviendas / Edificaciones',
                options=['Descargar de OpenStreetMap (Overpass API)', 'Usar Capa Vectorial Existente'],
                defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.BUILDINGS_LAYER,
                'Capa de Viviendas Existente (si seleccionó usar capa)',
                types=[QgsProcessing.TypeVectorPolygon, QgsProcessing.TypeVectorPoint],
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_VIAS,
                'Calles Preparadas (Vías)',
                type=QgsProcessing.TypeVectorLine
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_CASAS,
                'Viviendas Preparadas (Centroides)',
                type=QgsProcessing.TypeVectorPoint
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        boundary_source = self.parameterAsSource(parameters, self.INPUT_BOUNDARY, context)
        streets_mode = self.parameterAsEnum(parameters, self.STREETS_MODE, context)
        streets_layer = self.parameterAsVectorLayer(parameters, self.STREETS_LAYER, context)
        buildings_mode = self.parameterAsEnum(parameters, self.BUILDINGS_MODE, context)
        buildings_layer = self.parameterAsVectorLayer(parameters, self.BUILDINGS_LAYER, context)

        crs_project = boundary_source.sourceCrs()

        # Obtener bounding box en WGS84 para Overpass si se requiere
        xform_to_wgs84 = QgsCoordinateTransform(crs_project, QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance())
        extent_geom = QgsGeometry.fromRect(boundary_source.sourceExtent())
        extent_wgs84 = extent_geom.boundingBox()
        extent_wgs84_transformed = xform_to_wgs84.transform(extent_geom).boundingBox()

        # 1. Preparar Campos
        fields_vias = QgsFields()
        fields_vias.append(QgsField('id_via', QVariant.String, len=50))
        fields_vias.append(QgsField('nombre', QVariant.String, len=100))
        fields_vias.append(QgsField('tipo', QVariant.String, len=50))
        fields_vias.append(QgsField('longitud_m', QVariant.Double, prec=2))

        (sink_vias, dest_id_vias) = self.parameterAsSink(
            parameters, self.OUTPUT_VIAS, context, fields_vias, QgsWkbTypes.LineString, crs_project
        )

        fields_casas = QgsFields()
        fields_casas.append(QgsField('id_casa', QVariant.String, len=50))
        fields_casas.append(QgsField('x_utm', QVariant.Double, prec=3))
        fields_casas.append(QgsField('y_utm', QVariant.Double, prec=3))
        fields_casas.append(QgsField('area_edif', QVariant.Double, prec=2))
        fields_casas.append(QgsField('estado', QVariant.String, len=50))

        (sink_casas, dest_id_casas) = self.parameterAsSink(
            parameters, self.OUTPUT_CASAS, context, fields_casas, QgsWkbTypes.Point, crs_project
        )

        # 2. Procesar Calles
        feedback.pushInfo("Procesando calles...")
        if streets_mode == 1 and streets_layer:
            # Usar capa existente recortada o seleccionada por intersección
            via_count = 0
            for feat in streets_layer.getFeatures():
                geom = feat.geometry()
                if geom and not geom.isEmpty():
                    f_out = QgsFeature(fields_vias)
                    f_out.setGeometry(geom)
                    via_count += 1
                    nom = feat.attribute('nombre') or feat.attribute('name') or f"Calle {via_count}"
                    tipo = feat.attribute('tipo') or feat.attribute('highway') or "residential"
                    f_out.setAttributes([f"VIA-{via_count:03d}", str(nom), str(tipo), round(geom.length(), 2)])
                    sink_vias.addFeature(f_out, QgsFeatureSink.FastInsert)
            feedback.pushInfo(f"Se cargaron {via_count} tramos de vías desde la capa vectorial.")
        else:
            # Descarga Overpass API
            south = extent_wgs84_transformed.yMinimum()
            west = extent_wgs84_transformed.xMinimum()
            north = extent_wgs84_transformed.yMaximum()
            east = extent_wgs84_transformed.xMaximum()
            query = f"""
            [out:json][timeout:30];
            (
              way["highway"]({south:.6f},{west:.6f},{north:.6f},{east:.6f});
            );
            out body;
            >;
            out skel qt;
            """
            feedback.pushInfo(f"Consultando Overpass API para vías...")
            try:
                url = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query)
                req = urllib.request.Request(url, headers={'User-Agent': 'AquaRed-QGIS-Plugin/1.0'})
                with urllib.request.urlopen(req, timeout=35) as resp:
                    osm_data = json.loads(resp.read().decode('utf-8'))

                nodes_dict = {el['id']: (el['lon'], el['lat']) for el in osm_data.get('elements', []) if el.get('type') == 'node'}
                xform_from_wgs84 = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), crs_project, QgsProject.instance())

                via_count = 0
                for el in osm_data.get('elements', []):
                    if el.get('type') == 'way' and 'highway' in el.get('tags', {}):
                        tags = el.get('tags', {})
                        pts_layer = []
                        for nid in el.get('nodes', []):
                            if nid in nodes_dict:
                                lon, lat = nodes_dict[nid]
                                pt_proj = xform_from_wgs84.transform(QgsPointXY(lon, lat))
                                pts_layer.append(pt_proj)
                        if len(pts_layer) >= 2:
                            geom_line = QgsGeometry.fromPolylineXY(pts_layer)
                            via_count += 1
                            nom = tags.get('name', f"Calle {via_count}")
                            hw_type = tags.get('highway', 'residential')
                            f_out = QgsFeature(fields_vias)
                            f_out.setGeometry(geom_line)
                            f_out.setAttributes([f"VIA-{via_count:03d}", nom, hw_type, round(geom_line.length(), 2)])
                            sink_vias.addFeature(f_out, QgsFeatureSink.FastInsert)
                feedback.pushInfo(f"Descargadas {via_count} vías desde OSM.")
            except Exception as e:
                feedback.reportError(f"Error descargando vías desde Overpass API: {str(e)}")

        # 3. Procesar Viviendas
        feedback.pushInfo("Procesando viviendas...")
        if buildings_mode == 1 and buildings_layer:
            casa_count = 0
            for feat in buildings_layer.getFeatures():
                geom = feat.geometry()
                if geom and not geom.isEmpty():
                    pt = geom.centroid().asPoint()
                    casa_count += 1
                    area_val = geom.area() if geom.type() == QgsWkbTypes.PolygonGeometry else 0.0
                    f_out = QgsFeature(fields_casas)
                    f_out.setGeometry(QgsGeometry.fromPointXY(pt))
                    f_out.setAttributes([f"CASA-{casa_count:03d}", round(pt.x(), 3), round(pt.y(), 3), round(area_val, 2), "habitable"])
                    sink_casas.addFeature(f_out, QgsFeatureSink.FastInsert)
            feedback.pushInfo(f"Se cargaron {casa_count} viviendas desde la capa vectorial.")
        else:
            # Overpass API buildings
            south = extent_wgs84_transformed.yMinimum()
            west = extent_wgs84_transformed.xMinimum()
            north = extent_wgs84_transformed.yMaximum()
            east = extent_wgs84_transformed.xMaximum()
            query_b = f"""
            [out:json][timeout:35];
            (
              way["building"]({south:.6f},{west:.6f},{north:.6f},{east:.6f});
            );
            out body;
            >;
            out skel qt;
            """
            feedback.pushInfo(f"Consultando Overpass API para viviendas...")
            try:
                url_b = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query_b)
                req_b = urllib.request.Request(url_b, headers={'User-Agent': 'AquaRed-QGIS-Plugin/1.0'})
                with urllib.request.urlopen(req_b, timeout=40) as resp:
                    osm_b_data = json.loads(resp_b.read().decode('utf-8'))

                b_nodes = {el['id']: (el['lon'], el['lat']) for el in osm_b_data.get('elements', []) if el.get('type') == 'node'}
                xform_from_wgs84 = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), crs_project, QgsProject.instance())

                casa_count = 0
                for el in osm_b_data.get('elements', []):
                    if el.get('type') == 'way' and 'building' in el.get('tags', {}):
                        pts = []
                        for nid in el.get('nodes', []):
                            if nid in b_nodes:
                                lon, lat = b_nodes[nid]
                                pt_p = xform_from_wgs84.transform(QgsPointXY(lon, lat))
                                pts.append(pt_p)
                        if len(pts) >= 3:
                            poly_geom = QgsGeometry.fromPolygonXY([pts])
                            centroid_pt = poly_geom.centroid().asPoint()
                            casa_count += 1
                            f_out = QgsFeature(fields_casas)
                            f_out.setGeometry(QgsGeometry.fromPointXY(centroid_pt))
                            f_out.setAttributes([f"CASA-{casa_count:03d}", round(centroid_pt.x(), 3), round(centroid_pt.y(), 3), round(poly_geom.area(), 2), "habitable"])
                            sink_casas.addFeature(f_out, QgsFeatureSink.FastInsert)
                feedback.pushInfo(f"Descargadas {casa_count} viviendas desde OSM.")
            except Exception as e:
                feedback.reportError(f"Error descargando viviendas desde Overpass API: {str(e)}")

        return {
            self.OUTPUT_VIAS: dest_id_vias,
            self.OUTPUT_CASAS: dest_id_casas
        }
