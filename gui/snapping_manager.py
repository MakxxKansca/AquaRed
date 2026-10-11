"""
AquaRed - Gestor de Auto-Snapping y Edición Topológica
======================================================
Configura automáticamente las reglas de auto-ensamblado (snapping)
en el proyecto activo de QGIS y asiste en la activación de la herramienta
de vértices para ajustes de trazado.
"""

from qgis.core import (
    QgsProject,
    QgsSnappingConfig,
    QgsTolerance,
    QgsVectorLayer
)

class SnappingManager:
    @staticmethod
    def configurar_snapping_proyecto(tolerancia_m=0.75, habilitar_intersecciones=True, edicion_topologica=True):
        """
        Aplica la configuración de auto-snapping recomendada para redes hidráulicas:
         - Modo: Vértice y Segmento en todas las capas del proyecto
         - Tolerancia: expresada en unidades de mapa (metros)
         - Auto-ensamblado en intersecciones activado
         - Edición topológica activada para mantener la conectividad al mover vértices
        """
        proj = QgsProject.instance()
        snap_cfg = proj.snappingConfig()

        snap_cfg.setEnabled(True)
        # Modo: todas las capas visibles / activas
        snap_cfg.setMode(QgsSnappingConfig.AllLayers)
        # Tipos: vértice y segmento
        snap_cfg.setTypeFlag(QgsSnappingConfig.VertexFlag | QgsSnappingConfig.SegmentFlag)
        # Unidades de mapa (metros en proyecciones UTM)
        snap_cfg.setUnits(QgsTolerance.ProjectUnits)
        snap_cfg.setTolerance(float(tolerancia_m))
        snap_cfg.setIntersectionSnapping(bool(habilitar_intersecciones))

        proj.setSnappingConfig(snap_cfg)
        proj.setTopologicalEditing(bool(edicion_topologica))

        return True

    @staticmethod
    def activar_edicion_capa(iface, layer):
        """Pone una capa vectorial en modo de edición si no lo está ya."""
        if isinstance(layer, QgsVectorLayer) and layer.isValid():
            if not layer.isEditable():
                layer.startEditing()
            if iface:
                iface.setActiveLayer(layer)
            return True
        return False
