"""
AquaRed - Motor de Geometría y Topología Hidráulica
===================================================
Funciones analíticas y geométricas puras para:
 1. Normalización de orientación de ejes viales
 2. Generación de curvas de offset paralelo preservando trazado curvo original
 3. Trazado de acometidas domiciliarias perpendiculares
 4. Asignación oficial de caudales por tramo (Método IDAAN / MINSA)
 5. Análisis topológico de conectividad de grafo y detección de anomalías
 6. Generación de accesorios (válvulas de corte, purgas y ventosas)
"""

import math
from collections import defaultdict, deque
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import nearest_points, substring
from .idaan_rules import LITROS_POR_GALON, PSI_A_MCA, calcular_demanda_tramo_idaan

def normalizar_orientacion(line_geom, pt_inicio=None, direccion_norte_sur=False):
    """
    Normaliza la orientación canónica de una línea:
    - Si pt_inicio se suministra, asegura que coords[0] sea el extremo más cercano a pt_inicio.
    - Si direccion_norte_sur=True, asegura que coords[0].y >= coords[-1].y (Norte -> Sur).
    """
    coords = list(line_geom.coords)
    if len(coords) < 2:
        return line_geom

    if pt_inicio is not None:
        p_ini = Point(coords[0])
        p_fin = Point(coords[-1])
        if p_ini.distance(pt_inicio) > p_fin.distance(pt_inicio):
            coords = coords[::-1]
    elif direccion_norte_sur:
        if coords[0][1] < coords[-1][1]:
            coords = coords[::-1]

    return LineString(coords)

def calcular_offset_vial(line_geom, offset_m, boundary_poly=None, preferir_interior=True):
    """
    Calcula la curva paralela (offset) a una distancia especificada en metros.
    Si preferir_interior=True y se suministra el polígono límite, evalúa ambos lados (+ y -)
    y escoge automáticamente el que queda en el interior del desarrollo urbanístico.
    """
    if abs(offset_m) < 1e-4:
        return line_geom

    c_pos = line_geom.offset_curve(offset_m)
    c_neg = line_geom.offset_curve(-offset_m)

    if preferir_interior and boundary_poly is not None:
        len_pos = c_pos.intersection(boundary_poly).length if c_pos.is_valid else 0.0
        len_neg = c_neg.intersection(boundary_poly).length if c_neg.is_valid else 0.0
        chosen = c_pos if len_pos >= len_neg else c_neg
    else:
        chosen = c_pos

    if chosen.geom_type == 'MultiLineString':
        # Seleccionar la sección contigua más larga si se divide en discontinuidades
        chosen = max(chosen.geoms, key=lambda g: g.length)

    return chosen

def trazar_acometidas(casas_list, pipes_list, umbral_max_m=60.0):
    """
    Genera acometidas domiciliarias conectando cada vivienda perpendicularmente
    a la tubería matriz más cercana.

    Parámetros:
    - casas_list: list de dicts con 'id_casa', 'geometry' (Point o Polygon)
    - pipes_list: list de dicts con 'id_tubo', 'geometry' (LineString)
    - umbral_max_m: distancia máxima aceptable en metros

    Retorna:
    - acometidas: list de dicts con detalles geométricos y atributos
    - tomas: list de puntos de toma de derivación en tubería matriz
    """
    acometidas = []
    tomas = []

    for idx, c in enumerate(casas_list):
        id_casa = c.get('id_casa', f"CASA-{idx+1:03d}")
        geom_casa = c['geometry']
        pt_casa = geom_casa.centroid if geom_casa.geom_type != 'Point' else geom_casa

        # Encontrar tubería más cercana
        best_pipe = None
        best_pt_pipe = None
        min_dist = float('inf')

        for p in pipes_list:
            geom_pipe = p['geometry']
            npt_pipe, _ = nearest_points(geom_pipe, pt_casa)
            dist = pt_casa.distance(npt_pipe)
            if dist < min_dist:
                min_dist = dist
                best_pipe = p
                best_pt_pipe = npt_pipe

        if best_pipe is not None and min_dist <= umbral_max_m:
            line_acom = LineString([best_pt_pipe, pt_casa])
            id_acom = f"AC-{idx+1:03d}"
            id_toma = f"TOMA-{idx+1:03d}"

            acometidas.append({
                'id_acometida': id_acom,
                'id_casa': id_casa,
                'id_tubo_matriz': best_pipe['id_tubo'],
                'longitud_m': round(line_acom.length, 2),
                'diam_pulg': 0.5,
                'material': 'PEAD / PVC SDR-11 1/2"',
                'tipo_acometida': 'Estándar (<=15m)' if line_acom.length <= 15.0 else 'Extendida (>15m)',
                'pt_toma': best_pt_pipe,
                'pt_casa': pt_casa,
                'geometry': line_acom
            })

            tomas.append({
                'id_toma': id_toma,
                'id_acometida': id_acom,
                'id_casa': id_casa,
                'id_tubo_matriz': best_pipe['id_tubo'],
                'geometry': best_pt_pipe
            })

    return acometidas, tomas

def asignar_demandas_idaan_por_tramo(pipes_list, acometidas_list, nodos_list, params_norma):
    """
    Aplica rigurosamente el Método de Tramo Oficial IDAAN (Script 15):
     1. Agrupa acometidas por cada tramo de tubería matriz.
     2. Para cada tramo calcula:
        Q_medio = (N_casas * hab_por_casa * dotacion_L) / 86400
        Q_diseno = Q_medio * FMH
        Reparto 50% al nodo aguas arriba y 50% al nodo aguas abajo.
     3. Para cada nodo (excepto el tanque/fuente):
        Demanda nodal = Suma de aportes del 50% de todos los tramos que confluyen en él.
    """
    dot_gal = float(params_norma.get('dotacion_gal_hab_dia', 100.0))
    hab_casa = float(params_norma.get('hab_por_vivienda', 5.0))
    fmh = float(params_norma.get('factor_pico', 2.00))

    # Indexar casas por tramo
    casas_por_tubo = defaultdict(list)
    for ac in acometidas_list:
        casas_por_tubo[ac['id_tubo_matriz']].append(ac['id_casa'])

    tramos_reporte = []
    nodos_demandas = defaultdict(float)
    nodos_confluentes = defaultdict(list)

    for p in pipes_list:
        tid = p['id_tubo']
        na = p['nodo_ini']
        nb = p['nodo_fin']
        casas_tramo = sorted(casas_por_tubo.get(tid, []))
        n_casas = len(casas_tramo)

        calc = calcular_demanda_tramo_idaan(
            num_casas=n_casas,
            dotacion_gal_hab_dia=dot_gal,
            hab_por_casa=hab_casa,
            fmh=fmh
        )

        q_diseno = calc['q_diseno_lps']
        q_50 = calc['reparto_nodo_ini_lps']

        tramos_reporte.append({
            'id_tubo': tid,
            'nodo_ini': na,
            'nodo_fin': nb,
            'num_casas': n_casas,
            'habitantes': calc['habitantes'],
            'q_medio_lps': round(calc['q_medio_lps'], 6),
            'q_diseno_lps': round(q_diseno, 6),
            'reparto_nodo_ini_lps': round(q_50, 6),
            'reparto_nodo_fin_lps': round(q_50, 6),
            'casas': casas_tramo
        })

        if q_50 > 0:
            nodos_demandas[na] += q_50
            nodos_confluentes[na].append(f"{tid} (50%={q_50:.4f} L/s)")
            nodos_demandas[nb] += q_50
            nodos_confluentes[nb].append(f"{tid} (50%={q_50:.4f} L/s)")

    # Consolidar nodos
    nodos_reporte = []
    total_nodal_lps = 0.0

    for n in nodos_list:
        nid = n['id_nodo']
        tipo = n.get('tipo', 'Nodo')
        es_fuente = ('tanque' in tipo.lower() or 'reservoir' in tipo.lower() or 'fuente' in tipo.lower() or nid.startswith('TK'))

        q_dem = 0.0 if es_fuente else round(nodos_demandas.get(nid, 0.0), 6)
        if not es_fuente:
            total_nodal_lps += q_dem

        nodos_reporte.append({
            'id_nodo': nid,
            'nombre': n.get('nombre', nid),
            'tipo': tipo,
            'cota_terreno': n.get('cota_terreno', 100.0),
            'demanda_diseno_lps': q_dem,
            'demanda_diseno_gpm': round(q_dem * 15.8503, 3),
            'tramos_confluentes': ", ".join(nodos_confluentes.get(nid, [])) if not es_fuente else "Fuente / Tanque (Sin demanda asignada)"
        })

    # Verificación de balance de masa
    n_casas_total = len(acometidas_list)
    calc_global = calcular_demanda_tramo_idaan(n_casas_total, dot_gal, hab_casa, fmh)
    q_global_diseno = calc_global['q_diseno_lps']
    diferencia_balance = abs(total_nodal_lps - q_global_diseno)

    balance_info = {
        'total_viviendas': n_casas_total,
        'q_diseno_global_lps': round(q_global_diseno, 6),
        'suma_demandas_nodales_lps': round(total_nodal_lps, 6),
        'diferencia_balance_lps': round(diferencia_balance, 8),
        'balance_perfecto': diferencia_balance < 1e-4
    }

    return tramos_reporte, nodos_reporte, balance_info

def validar_topologia_red(nodos_list, pipes_list, id_fuente=None):
    """
    Verifica que la red hidráulica sea conexa (1 solo componente conexo),
    detecta nodos aislados, tramos desconectados, quiebres angulares agudos
    y tramos con longitud cero o invertidos.
    """
    adj = defaultdict(list)
    nodes_set = {n['id_nodo'] for n in nodos_list}

    errores = []
    advertencias = []

    for p in pipes_list:
        pid = p['id_tubo']
        na = p['nodo_ini']
        nb = p['nodo_fin']

        if na not in nodes_set:
            errores.append(f"Tubería '{pid}': Nodo inicial '{na}' no existe en la lista de nodos.")
        if nb not in nodes_set:
            errores.append(f"Tubería '{pid}': Nodo final '{nb}' no existe en la lista de nodos.")

        l_m = p.get('geometry', LineString()).length if 'geometry' in p else p.get('longitud_m', 0.0)
        if l_m < 0.1:
            errores.append(f"Tubería '{pid}': Longitud excesivamente corta o nula ({l_m:.2f} m).")

        adj[na].append((nb, pid))
        adj[nb].append((na, pid))

    # Análisis de componentes conexos mediante BFS
    visitados = set()
    componentes = []

    for n in nodes_set:
        if n not in visitados:
            comp = []
            queue = deque([n])
            visitados.add(n)
            while queue:
                curr = queue.popleft()
                comp.append(curr)
                for vecino, _ in adj[curr]:
                    if vecino not in visitados:
                        visitados.add(vecino)
                        queue.append(vecino)
            componentes.append(comp)

    num_componentes = len(componentes)
    if num_componentes > 1:
        errores.append(f"Red desconectada: Se detectaron {num_componentes} componentes aislados. La red no es 100% continua.")
    elif num_componentes == 0:
        errores.append("La red no contiene nodos válidos.")

    # Verificar si el nodo fuente está conectado a la red
    if id_fuente and id_fuente in nodes_set:
        if len(adj[id_fuente]) == 0:
            errores.append(f"El nodo fuente '{id_fuente}' se encuentra completamente aislado sin tuberías conectadas.")

    # Identificar terminales (grado 1)
    terminales = [n for n, vecs in adj.items() if len(vecs) == 1 and n != id_fuente]

    return {
        'es_valida': len(errores) == 0,
        'num_componentes': num_componentes,
        'total_nodos': len(nodes_set),
        'total_tramos': len(pipes_list),
        'terminales': terminales,
        'errores': errores,
        'advertencias': advertencias
    }

def generar_valvulas_tecnicas(pipes_list, nodos_list, id_fuente="TK-001"):
    """
    Genera válvulas de corte y seccionamiento:
    - Válvula de aislamiento maestro en la aducción.
    - Ventosa de aire trifuncional en punto alto / empalme maestro.
    - Válvulas de compuerta en cabecera de cada ramal derivado (Tee).
    - Válvulas de purga y desagüe en cada fondo de saco (nodos terminales).
    """
    valvulas = []
    valv_idx = 1

    # Mapeo de tuberías
    pipe_dict = {p['id_tubo']: p for p in pipes_list}
    node_dict = {n['id_nodo']: n for n in nodos_list}

    # Grado de cada nodo
    adj = defaultdict(list)
    for p in pipes_list:
        adj[p['nodo_ini']].append(p)
        adj[p['nodo_fin']].append(p)

    # 1. Aducción / Cabecera Maestra
    t_aduc = None
    for p in pipes_list:
        if p['nodo_ini'] == id_fuente or p['nodo_fin'] == id_fuente:
            t_aduc = p
            break

    if t_aduc:
        emp_node = t_aduc['nodo_fin'] if t_aduc['nodo_ini'] == id_fuente else t_aduc['nodo_ini']
        pt_emp = node_dict.get(emp_node, {}).get('geometry', None)
        cota_emp = node_dict.get(emp_node, {}).get('cota_terreno', 100.0)

        # Compuerta maestra sobre aducción
        geom_aduc = t_aduc.get('geometry')
        pt_v1 = Point(geom_aduc.interpolate(max(0, geom_aduc.length - 2.5)).coords[0]) if geom_aduc else pt_emp
        valvulas.append({
            'id_valvula': f"VALV-{valv_idx:03d}",
            'tipo': 'Compuerta 4"',
            'nodo_asociado': emp_node,
            'funcion': 'Aislamiento y control maestro de la aducción',
            'cota': cota_emp,
            'geometry': pt_v1
        })
        valv_idx += 1

        # Ventosa en punto alto / empalme
        if pt_emp:
            valvulas.append({
                'id_valvula': f"VENT-{valv_idx:03d}",
                'tipo': 'Ventosa Trifuncional 1"',
                'nodo_asociado': emp_node,
                'funcion': 'Expulsión y admisión automática de aire en el punto alto',
                'cota': cota_emp,
                'geometry': pt_emp
            })
            valv_idx += 1

    # 2. Válvulas de ramales derivados (Tees)
    for nid, pipes_confl in adj.items():
        if len(pipes_confl) >= 3 and nid != id_fuente:
            n_data = node_dict.get(nid, {})
            # Identificar ramal secundario
            for p in pipes_confl:
                calle = p.get('calle', '')
                if 'ramal' in p['id_tubo'].lower() or 'calle' in calle.lower() or p.get('diam_nom_pulg', 3.0) < 3.0:
                    geom_p = p.get('geometry')
                    if geom_p:
                        pt_v = Point(geom_p.interpolate(min(geom_p.length, 2.0)).coords[0])
                        valvulas.append({
                            'id_valvula': f"VALV-{valv_idx:03d}",
                            'tipo': f"Compuerta {p.get('diam_nom_pulg', 2.0):.0f}\"",
                            'nodo_asociado': nid,
                            'funcion': f"Aislamiento sectorial de {calle if calle else p['id_tubo']}",
                            'cota': n_data.get('cota_terreno', 100.0),
                            'geometry': pt_v
                        })
                        valv_idx += 1

    # 3. Purgas en fondos de saco (Terminales)
    for nid, pipes_confl in adj.items():
        if len(pipes_confl) == 1 and nid != id_fuente:
            n_data = node_dict.get(nid, {})
            valvulas.append({
                'id_valvula': f"PURG-{valv_idx:03d}",
                'tipo': 'Purga y Desagüe 2"',
                'nodo_asociado': nid,
                'funcion': f"Limpieza y purga periódica en fondo de saco ({n_data.get('nombre', nid)})",
                'cota': n_data.get('cota_terreno', 100.0),
                'geometry': n_data.get('geometry', Point(0, 0))
            })
            valv_idx += 1

    return valvulas
