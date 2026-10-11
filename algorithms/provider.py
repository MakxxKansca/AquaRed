"""
AquaRed - Processing Provider para QGIS
=======================================
Registra la caja de herramientas de AquaRed dentro del panel de Procesos de QGIS.
"""

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os

from .step1_extraer_base import Step1ExtraerBaseAlgorithm
from .step2_dem_sampling import Step2DemSamplingAlgorithm
from .step3_trazar_offset import Step3TrazarOffsetAlgorithm
from .step4_acometidas import Step4AcometidasAlgorithm
from .step5_demandas_idaan import Step5DemandasIdaanAlgorithm
from .step6_validaciones import Step6ValidacionesAlgorithm
from .step7_exportar_inp import Step7ExportarInpAlgorithm

class AquaRedProvider(QgsProcessingProvider):

    def __init__(self):
        super().__init__()

    def id(self):
        return 'aquared'

    def name(self):
        return 'AquaRed'

    def icon(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icon.png')
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return super().icon()

    def longName(self):
        return 'AquaRed - Diseño de Redes Hidráulicas con Normativa IDAAN'

    def loadAlgorithms(self):
        self.addAlgorithm(Step1ExtraerBaseAlgorithm())
        self.addAlgorithm(Step2DemSamplingAlgorithm())
        self.addAlgorithm(Step3TrazarOffsetAlgorithm())
        self.addAlgorithm(Step4AcometidasAlgorithm())
        self.addAlgorithm(Step5DemandasIdaanAlgorithm())
        self.addAlgorithm(Step6ValidacionesAlgorithm())
        self.addAlgorithm(Step7ExportarInpAlgorithm())
