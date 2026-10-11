"""
AquaRed - Reglas y Parámetros Normativos IDAAN / MINSA (Panamá)
=============================================================
Define los parámetros de diseño hidráulico según la clasificación
del proyecto (Urbano vs Rural) y el catálogo técnico de tuberías.
"""

# Constantes de conversión
LITROS_POR_GALON = 3.785411784
PSI_A_MCA = 0.70306958

# Catálogo oficial de tuberías PVC SDR-26 (ASTM D2241) y PEAD
CATALOGO_TUBERIAS = {
    '4"': {'nom_pulg': 4.0, 'd_ext_mm': 114.3, 'd_int_mm': 105.5, 'material': 'PVC SDR-26', 'c_hw': 140.0},
    '3"': {'nom_pulg': 3.0, 'd_ext_mm': 88.9,  'd_int_mm': 82.1,  'material': 'PVC SDR-26', 'c_hw': 140.0},
    '2.5"': {'nom_pulg': 2.5, 'd_ext_mm': 73.0,  'd_int_mm': 67.4,  'material': 'PVC SDR-26', 'c_hw': 140.0},
    '2"': {'nom_pulg': 2.0, 'd_ext_mm': 60.3,  'd_int_mm': 55.7,  'material': 'PVC SDR-26', 'c_hw': 140.0},
    '1/2"': {'nom_pulg': 0.5, 'd_ext_mm': 20.0,  'd_int_mm': 16.0,  'material': 'PEAD SDR-11', 'c_hw': 150.0},
}

# Configuraciones base por clasificación
NORMAS = {
    'urbano': {
        'nombre': 'Urbano (Norma IDAAN)',
        'dotacion_gal_hab_dia': 100.0,
        'dotacion_l_hab_dia': 100.0 * LITROS_POR_GALON,  # 378.541 L/hab/día
        'presion_min_psi': 20.0,
        'presion_min_mca': 20.0 * PSI_A_MCA,             # 14.06 mca
        'presion_max_mca': 50.0,
        'diam_min_troncal': '4"',
        'diam_min_ramal': '3"',
        'factor_pico': 2.00,                             # FMH Urbano
        'hab_por_vivienda': 5.0,
        'profundidad_zanja_m': 1.15,
        'ancho_zanja_m': 0.60
    },
    'rural': {
        'nombre': 'Rural (Norma MINSA / IDAAN Rural)',
        'dotacion_gal_hab_dia': 80.0,
        'dotacion_l_hab_dia': 80.0 * LITROS_POR_GALON,   # 302.833 L/hab/dia
        'presion_min_psi': 14.0,
        'presion_min_mca': 14.0 * PSI_A_MCA,             # 10.00 mca (aprox 9.84 mca)
        'presion_max_mca': 50.0,
        'diam_min_troncal': '3"',
        'diam_min_ramal': '2"',
        'factor_pico': 2.16,                             # Kp = K1(1.2) * K2(1.8)
        'hab_por_vivienda': 5.0,
        'profundidad_zanja_m': 1.10,
        'ancho_zanja_m': 0.60
    }
}

def obtener_parametros_norma(tipo='urbano'):
    """Retorna los parámetros completos para 'urbano' o 'rural'."""
    tipo_key = str(tipo).lower().strip()
    if 'rur' in tipo_key:
        return dict(NORMAS['rural'])
    return dict(NORMAS['urbano'])

def calcular_demanda_tramo_idaan(num_casas, dotacion_gal_hab_dia=100.0, hab_por_casa=5.0, fmh=2.00):
    """
    Calcula el caudal de diseño por tramo según el Método Oficial IDAAN:
    - Q_medio = (num_casas * hab_por_casa * dotacion_L) / 86400
    - Q_diseno = Q_medio * fmh
    - Reparto: 50% al nodo aguas arriba, 50% al nodo aguas abajo.
    """
    dotacion_l = dotacion_gal_hab_dia * LITROS_POR_GALON
    hab_totales = float(num_casas) * float(hab_por_casa)
    q_med_lps = (hab_totales * dotacion_l) / 86400.0
    q_dis_lps = q_med_lps * float(fmh)
    reparto_50 = q_dis_lps * 0.50
    return {
        'habitantes': hab_totales,
        'q_medio_lps': q_med_lps,
        'q_diseno_lps': q_dis_lps,
        'reparto_nodo_ini_lps': reparto_50,
        'reparto_nodo_fin_lps': reparto_50
    }
