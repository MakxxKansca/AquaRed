"""
AquaRed - Gestor de Perfiles de Configuración (JSON)
===================================================
Permite guardar, cargar y restaurar perfiles de diseño hidráulico,
incluyendo plantillas predeterminadas para proyectos urbanos y rurales.
"""

import json
import os

PERFIL_URBANO_IDAAN = {
    "nombre_perfil": "Red Urbana / Residencial (Norma IDAAN 100 gal)",
    "clasificacion": "urbano",
    "dotacion_gal_hab_dia": 100.0,
    "presion_min_psi": 20.0,
    "diam_min_troncal": '4"',
    "diam_min_ramal": '3"',
    "factor_pico_fmh": 2.00,
    "hab_por_vivienda": 5.0,
    "offset_tuberias_m": 5.00,
    "lado_offset_preferencial": "interior",  # 'interior', 'left', 'right'
    "profundidad_zanja_m": 1.15,
    "ancho_zanja_m": 0.60,
    "altura_torre_tanque_m": 15.00,
    "cota_tanque_terreno_m": 100.00,
    "tolerancia_snapping_m": 0.75,
    "umbral_acometida_m": 15.0,
    "fuente_calles": "osm",      # 'osm' o 'layer'
    "fuente_casas": "osm",       # 'osm' o 'layer'
    "generar_capas": {
        "calles": True,
        "casas": True,
        "tuberias": True,
        "acometidas": True,
        "valvulas": True,
        "demandas": True,
        "exportar_inp": True
    }
}

PERFIL_RURAL_MINSA = {
    "nombre_perfil": "Red Rural / Comunitaria (Norma MINSA 80 gal)",
    "clasificacion": "rural",
    "dotacion_gal_hab_dia": 80.0,
    "presion_min_psi": 14.0,
    "diam_min_troncal": '3"',
    "diam_min_ramal": '2"',
    "factor_pico_fmh": 2.16,
    "hab_por_vivienda": 5.0,
    "offset_tuberias_m": 4.00,
    "lado_offset_preferencial": "interior",
    "profundidad_zanja_m": 1.10,
    "ancho_zanja_m": 0.60,
    "altura_torre_tanque_m": 15.00,
    "cota_tanque_terreno_m": 50.00,
    "tolerancia_snapping_m": 0.75,
    "umbral_acometida_m": 30.0,
    "fuente_calles": "osm",
    "fuente_casas": "osm",
    "generar_capas": {
        "calles": True,
        "casas": True,
        "tuberias": True,
        "acometidas": True,
        "valvulas": True,
        "demandas": True,
        "exportar_inp": True
    }
}

# Alias de compatibilidad
PERFIL_DEFAULT_ESHA = PERFIL_URBANO_IDAAN
PERFIL_RURAL_SAN_PEDRO = PERFIL_RURAL_MINSA

def obtener_perfil_predeterminado():
    """Retorna una copia del perfil predeterminado urbano."""
    return json.loads(json.dumps(PERFIL_URBANO_IDAAN))

def guardar_perfil_a_archivo(config_dict, file_path):
    """Guarda un diccionario de configuración como archivo JSON formateado."""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=4, ensure_ascii=False)
    return True

def cargar_perfil_desde_archivo(file_path):
    """Carga y valida un archivo JSON de perfil de usuario."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"El archivo de perfil no existe: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Rellenar claves faltantes con el default por seguridad
    perfil = obtener_perfil_predeterminado()
    perfil.update(data)
    return perfil
