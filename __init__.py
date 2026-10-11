"""
AquaRed - QGIS Plugin Initialization Entry Point
================================================
Función fábrica oficial classFactory requerida por la arquitectura de plugins de QGIS.
"""

def classFactory(iface):
    """Carga y retorna la instancia principal del plugin AquaRed."""
    from .plugin import AquaRedPlugin
    return AquaRedPlugin(iface)
