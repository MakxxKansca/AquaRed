"""
AquaRed - Algoritmo 5: Asignación Oficial de Demandas por Tramo (Normativa IDAAN / MINSA)
========================================================================================
Implementa rigurosamente el Método Oficial IDAAN por Tramo (Script 15):
 - Agrupa las viviendas asociadas a cada tramo de tubería matriz.
 - Calcula el caudal de diseño: Q_diseño = (N_casas * hab_casa * dotación_L) / 86400 * FMH.
 - Reparte el 50% del caudal al nodo aguas arriba y el 50% al nodo aguas abajo.
 - Asigna a cada nodo la suma exacta de los aportes del 50% de todos los tramos que confluyen en él.
 - Verifica el balance de masa global (0.00% error de balance).
"""

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterEnum,
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
from ..core.idaan_rules import obtener_parametros_norma
from ..core.topology_engine import asignar_demandas_idaan_por_tramo

class Step5DemandasIdaanAlgorithm(QgsProcessingAlgorithm):
    INPUT_TUBERIAS = 'INPUT_TUBERIAS'
    INPUT_ACOMETIDAS = 'INPUT_ACOMETIDAS'
    INPUT_NODOS = 'INPUT_NODOS'
    CLASIFICACION = 'CLASIFICACION'
    DOTACION = 'DOTACION'
    HAB_POR_CASA = 'HAB_POR_CASA'
    FACTOR_PICO = 'FACTOR_PICO'
    OUTPUT_NODOS_DEMANDA = 'OUTPUT_NODOS_DEMANDA'

    def createInstance(self):
        return Step5DemandasIdaanAlgorithm()

    def name(self):
        return 'step5_demandas_idaan'

    def displayName(self):
        return 'Paso 5: Asignar Demandas (Método Oficial Tramo IDAAN)'

    def group(self):
        return 'AquaRed - Flujo de Trabajo'

    def groupId(self):
        return 'aquared_workflow'

    def shortHelpString(self):
        return """
<b>Paso 5: Asignación de Demandas por Método Oficial de Tramo IDAAN (Script 15)</b><br><br>
Método oficial de reparto hidráulico para redes ramificadas y mallas en Panamá:<br>
 1. <b>Dotación y pico</b>: Determinado por la clasificación del proyecto (Urbano: 100 gal/hab/día, FMH=2.00; Rural: 80 gal/hab/día, FMH=2.16).<br>
 2. <b>Cálculo por tramo</b>: A partir del número de viviendas tributarias en cada tubería.<br>
 3. <b>Reparto biseccional</b>: 50% del caudal de diseño al nodo inicial y 50% al nodo final.<br>
 4. <b>Demanda nodal</b>: Suma algebraica de los aportes de todos los tramos incidentes.<br>
 5. <b>Balance de masa</b>: Verifica matemáticamente que la suma nodal iguale el 100.00% del consumo del acueducto.<br>
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
                self.INPUT_ACOMETIDAS,
                'Capa de Acometidas Domiciliarias',
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
            QgsProcessingParameterEnum(
                self.CLASIFICACION,
                'Clasificación del Proyecto',
                options=['Urbano (100 gal/hab/día, 20 psi min, FMH=2.00)', 'Rural (80 gal/hab/día, 14 psi min, FMH=2.16)'],
                defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.DOTACION,
                'Dotación de Consumo (gal/hab/día)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=100.0,
                minValue=30.0,
                maxValue=250.0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.HAB_POR_CASA,
                'Densidad Habitacional (hab/vivienda)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=5.0,
                minValue=1.0,
                maxValue=15.0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.FACTOR_PICO,
                'Factor de Caudal Máximo Horario (FMH)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=2.00,
                minValue=1.0,
                maxValue=4.0
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_NODOS_DEMANDA,
                'Nodos con Demandas Nodales Asignadas',
                type=QgsProcessing.TypeVectorPoint
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        tub_source = self.parameterAsSource(parameters, self.INPUT_TUBERIAS, context)
        ac_source = self.parameterAsSource(parameters, self.INPUT_ACOMETIDAS, context)
        nod_source = self.parameterAsSource(parameters, self.INPUT_NODOS, context)

        clasif_idx = self.parameterAsEnum(parameters, self.CLASIFICACION, context)
        clasif_str = 'urbano' if clasif_idx == 0 else 'rural'
        params_base = obtener_parametros_norma(clasif_str)

        # Sobrescribir con valores del diálogo si fueron modificados
        params_norma = dict(params_base)
        params_norma['dotacion_gal_hab_dia'] = self.parameterAsDouble(parameters, self.DOTACION, context)
        params_norma['hab_por_vivienda'] = self.parameterAsDouble(parameters, self.HAB_POR_CASA, context)
        params_norma['factor_pico'] = self.parameterAsDouble(parameters, self.FACTOR_PICO, context)

        crs = nod_source.sourceCrs()

        # Extraer tuberías
        pipes_list = []
        for feat in tub_source.getFeatures():
            tid = feat.attribute('id_tubo') or feat.attribute('id')
            na = feat.attribute('nodo_ini')
            nb = feat.attribute('nodo_fin')
            pipes_list.append({
                'id_tubo': str(tid),
                'nodo_ini': str(na),
                'nodo_fin': str(nb)
            })

        # Extraer acometidas
        acometidas_list = []
        for feat in ac_source.getFeatures():
            cid = feat.attribute('id_casa')
            t_mat = feat.attribute('id_tubo_matriz') or feat.attribute('id_tubo')
            acometidas_list.append({
                'id_casa': str(cid),
                'id_tubo_matriz': str(t_mat)
            })

        # Extraer nodos
        nodos_list = []
        geom_map = {}
        for feat in nod_source.getFeatures():
            nid = feat.attribute('id_nodo') or feat.attribute('id')
            nom = feat.attribute('nombre') or str(nid)
            tipo = feat.attribute('tipo') or "Nodo"
            cota = feat.attribute('cota_terreno') or 100.0
            g = feat.geometry()
            geom_map[str(nid)] = g
            nodos_list.append({
                'id_nodo': str(nid),
                'nombre': str(nom),
                'tipo': str(tipo),
                'cota_terreno': float(cota)
            })

        feedback.pushInfo(f"Calculando asignación oficial IDAAN para {len(acometidas_list)} viviendas en {len(pipes_list)} tramos...")
        tramos_rep, nodos_rep, balance = asignar_demandas_idaan_por_tramo(
            pipes_list, acometidas_list, nodos_list, params_norma
        )

        feedback.pushInfo("═══════════════════════════════════════════════════════════")
        feedback.pushInfo(f"BALANCE DE MASA HIDRÁULICO (MÉTODO TRAMO IDAAN)")
        feedback.pushInfo(f" • Viviendas Totales:           {balance['total_viviendas']}")
        feedback.pushInfo(f" • Caudal Diseño Total:         {balance['q_diseno_global_lps']:.6f} L/s")
        feedback.pushInfo(f" • Suma de Demandas Nodales:    {balance['suma_demandas_nodales_lps']:.6f} L/s")
        feedback.pushInfo(f" • Diferencia de Balance:       {balance['diferencia_balance_lps']:.10f} L/s")
        feedback.pushInfo(f" • Estado:                      {'100.00% BALANCE PERFECTO' if balance['balance_perfecto'] else 'DESBALANCE'}")
        feedback.pushInfo("═══════════════════════════════════════════════════════════")

        # Preparar campos de salida
        fields_nod = QgsFields()
        fields_nod.append(QgsField('id_nodo', QVariant.String, len=50))
        fields_nod.append(QgsField('nombre', QVariant.String, len=100))
        fields_nod.append(QgsField('tipo', QVariant.String, len=50))
        fields_nod.append(QgsField('cota_terreno', QVariant.Double, prec=2))
        fields_nod.append(QgsField('demanda_diseno_lps', QVariant.Double, prec=6))
        fields_nod.append(QgsField('demanda_diseno_gpm', QVariant.Double, prec=3))
        fields_nod.append(QgsField('tramos_confluentes', QVariant.String, len=254))

        (sink_nod, dest_id_nod) = self.parameterAsSink(
            parameters, self.OUTPUT_NODOS_DEMANDA, context, fields_nod, QgsWkbTypes.Point, crs
        )

        for nr in nodos_rep:
            nid = nr['id_nodo']
            g = geom_map.get(nid)
            f = QgsFeature(fields_nod)
            if g:
                f.setGeometry(g)
            f.setAttributes([
                nid, nr['nombre'], nr['tipo'], nr['cota_terreno'],
                nr['demanda_diseno_lps'], nr['demanda_diseno_gpm'], nr['tramos_confluentes']
            ])
            sink_nod.addFeature(f, QgsFeatureSink.FastInsert)

        return {self.OUTPUT_NODOS_DEMANDA: dest_id_nod}
