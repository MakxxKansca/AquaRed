"""
AquaRed Core Module
"""

from .idaan_rules import (
    NORMAS,
    CATALOGO_TUBERIAS,
    obtener_parametros_norma,
    calcular_demanda_tramo_idaan,
    LITROS_POR_GALON,
    PSI_A_MCA
)

from .profile_manager import (
    obtener_perfil_predeterminado,
    guardar_perfil_a_archivo,
    cargar_perfil_desde_archivo
)

from .epanet_exporter import EpanetExporter

from .topology_engine import (
    normalizar_orientacion,
    calcular_offset_vial,
    trazar_acometidas,
    asignar_demandas_idaan_por_tramo,
    validar_topologia_red,
    generar_valvulas_tecnicas
)
