"""
AquaRed - Exportador Autónomo a EPANET (.INP)
============================================
Genera archivos ASCII de entrada para EPANET 2.0 / 2.2 de forma 100% nativa,
sin requerir dependencias externas como WNTR.
Incluye soporte para:
 - Unidades métricas (LPS)
 - Nodos (Junctions con elevación y demanda de diseño)
 - Reservorios / Tanques con cota piezométrica
 - Tuberías con longitud, diámetro interno en mm y rugosidad Hazen-Williams
 - Vértices intermedios de curvatura para trazado idéntico a QGIS
 - Coordenadas UTM exactas
 - Encuadre espacial de fondo [BACKDROP]
 - Patrón horario de modulación de demanda (24 horas)
"""

import os
import math

class EpanetExporter:
    def __init__(self, title="AquaRed - Modelo de Red de Agua Potable"):
        self.title = title
        self.junctions = []   # list of dicts: {'id': str, 'elev': float, 'demand_lps': float, 'pattern': str}
        self.reservoirs = []  # list of dicts: {'id': str, 'head': float, 'pattern': str}
        self.pipes = []       # list of dicts: {'id': str, 'node1': str, 'node2': str, 'length': float, 'diameter_mm': float, 'roughness': float, 'minor_loss': float, 'status': str, 'vertices': list of (x,y)}
        self.coordinates = {} # dict: {node_id: (x, y)}
        self.patterns = {
            "PATRON_HORARIO": [
                0.175, 0.150, 0.125, 0.150, 0.275, 0.550,
                1.000, 0.900, 0.650, 0.530, 0.600, 0.950,
                0.830, 0.510, 0.420, 0.390, 0.490, 0.690,
                0.650, 0.510, 0.370, 0.280, 0.210, 0.180
            ]
        }
        self.backdrop_margin = 25.0

    def add_junction(self, node_id, elevation, demand_lps=0.0, pattern="PATRON_HORARIO", x=None, y=None):
        self.junctions.append({
            'id': str(node_id),
            'elev': float(elevation),
            'demand_lps': float(demand_lps),
            'pattern': pattern if pattern else ""
        })
        if x is not None and y is not None:
            self.coordinates[str(node_id)] = (float(x), float(y))

    def add_reservoir(self, node_id, total_head, pattern="", x=None, y=None):
        self.reservoirs.append({
            'id': str(node_id),
            'head': float(total_head),
            'pattern': pattern
        })
        if x is not None and y is not None:
            self.coordinates[str(node_id)] = (float(x), float(y))

    def add_pipe(self, pipe_id, node1, node2, length_m, diameter_mm, roughness=140.0, minor_loss=0.0, status="Open", vertices=None):
        self.pipes.append({
            'id': str(pipe_id),
            'node1': str(node1),
            'node2': str(node2),
            'length': float(length_m),
            'diameter_mm': float(diameter_mm),
            'roughness': float(roughness),
            'minor_loss': float(minor_loss),
            'status': status,
            'vertices': vertices if vertices else []
        })

    def set_pattern(self, name, multipliers_list):
        self.patterns[name] = [float(m) for m in multipliers_list]

    def export_inp(self, file_path):
        """Escribe el archivo .INP completo formateado según la especificación EPANET."""
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        lines = []
        lines.append("[TITLE]")
        lines.append(f"; {self.title}")
        lines.append("")

        # [JUNCTIONS]
        lines.append("[JUNCTIONS]")
        lines.append(";ID              Elevation       Demand          Pattern")
        for j in self.junctions:
            pat_str = j['pattern'] if j['pattern'] else ""
            lines.append(f" {j['id']:<15} {j['elev']:<15.2f} {j['demand_lps']:<15.6f} {pat_str:<15}")
        lines.append("")

        # [RESERVOIRS]
        lines.append("[RESERVOIRS]")
        lines.append(";ID              Head            Pattern")
        for r in self.reservoirs:
            lines.append(f" {r['id']:<15} {r['head']:<15.2f} {r['pattern']:<15}")
        lines.append("")

        # [TANKS] (Vacío si sólo se modelan fuentes tipo Reservorio/Embalse)
        lines.append("[TANKS]")
        lines.append(";ID              Elevation       InitLevel       MinLevel        MaxLevel        Diameter        MinVol          VolCurve")
        lines.append("")

        # [PIPES]
        lines.append("[PIPES]")
        lines.append(";ID              Node1           Node2           Length          Diameter        Roughness       MinorLoss       Status")
        for p in self.pipes:
            lines.append(
                f" {p['id']:<15} {p['node1']:<15} {p['node2']:<15} "
                f"{p['length']:<15.3f} {p['diameter_mm']:<15.2f} "
                f"{p['roughness']:<15.1f} {p['minor_loss']:<15.2f} {p['status']:<10}"
            )
        lines.append("")

        # [PUMPS], [VALVES], [TAGS], [DEMANDS], [STATUS]
        lines.append("[PUMPS]")
        lines.append(";ID              Node1           Node2           Parameters")
        lines.append("")

        lines.append("[VALVES]")
        lines.append(";ID              Node1           Node2           Diameter   Type   Setting   MinorLoss")
        lines.append("")

        lines.append("[TAGS]")
        lines.append("")

        lines.append("[DEMANDS]")
        lines.append("")

        lines.append("[STATUS]")
        lines.append("")

        # [PATTERNS]
        lines.append("[PATTERNS]")
        lines.append(";ID              Multipliers")
        for pat_name, mults in self.patterns.items():
            # Formatear de 6 en 6
            for i in range(0, len(mults), 6):
                chunk = mults[i:i+6]
                vals_str = " ".join(f"{v:.6f}" for v in chunk)
                lines.append(f" {pat_name:<15} {vals_str}")
        lines.append("")

        # [CURVES], [CONTROLS], [RULES], [ENERGY], [EMITTERS], [QUALITY], [SOURCES], [REACTIONS], [MIXING]
        lines.append("[CURVES]")
        lines.append("")
        lines.append("[CONTROLS]")
        lines.append("")
        lines.append("[RULES]")
        lines.append("")
        lines.append("[ENERGY]")
        lines.append(" GLOBAL PRICE           0.0000")
        lines.append("")
        lines.append("[EMITTERS]")
        lines.append("")
        lines.append("[QUALITY]")
        lines.append("")
        lines.append("[SOURCES]")
        lines.append("")
        lines.append("[REACTIONS]")
        lines.append(" ORDER BULK 1")
        lines.append(" ORDER TANK 1")
        lines.append(" ORDER WALL 1")
        lines.append(" GLOBAL BULK 0.0000")
        lines.append(" GLOBAL WALL 0.0000")
        lines.append("")
        lines.append("[MIXING]")
        lines.append("")

        # [TIMES]
        lines.append("[TIMES]")
        lines.append(" DURATION             24:00:00")
        lines.append(" HYDRAULIC TIMESTEP   01:00:00")
        lines.append(" QUALITY TIMESTEP     00:06:00")
        lines.append(" PATTERN TIMESTEP     01:00:00")
        lines.append(" PATTERN START        00:00:00")
        lines.append(" REPORT TIMESTEP      01:00:00")
        lines.append(" REPORT START         00:00:00")
        lines.append(" START CLOCKTIME      00:00:00 AM")
        lines.append(" RULE TIMESTEP        00:06:00")
        lines.append(" STATISTIC            NONE")
        lines.append("")

        # [REPORT]
        lines.append("[REPORT]")
        lines.append(" Status               Yes")
        lines.append(" Summary              No")
        lines.append(" Page                 0")
        lines.append("")

        # [OPTIONS]
        lines.append("[OPTIONS]")
        lines.append(" UNITS                LPS")
        lines.append(" HEADLOSS             H-W")
        lines.append(" SPECIFIC GRAVITY     1.0")
        lines.append(" VISCOSITY            1.0")
        lines.append(" TRIALS               200")
        lines.append(" ACCURACY             0.001")
        lines.append(" CHECKFREQ            2")
        lines.append(" MAXCHECK             10")
        lines.append(" UNBALANCED           STOP")
        lines.append(" PATTERN              PATRON_HORARIO")
        lines.append(" DEMAND MULTIPLIER    1.0")
        lines.append(" EMITTER EXPONENT     0.5")
        lines.append(" QUALITY              NONE")
        lines.append(" DIFFUSIVITY          1.0")
        lines.append(" TOLERANCE            0.01")
        lines.append("")

        # [COORDINATES]
        lines.append("[COORDINATES]")
        lines.append(";Node            X-Coord              Y-Coord")
        all_xs, all_ys = [], []
        for nid, (x, y) in self.coordinates.items():
            lines.append(f" {nid:<15} {x:<20.3f} {y:<20.3f}")
            all_xs.append(x)
            all_ys.append(y)
        lines.append("")

        # [VERTICES]
        lines.append("[VERTICES]")
        lines.append(";Pipe            X-Coord              Y-Coord")
        for p in self.pipes:
            for vx, vy in p['vertices']:
                lines.append(f" {p['id']:<15} {vx:<20.3f} {vy:<20.3f}")
                all_xs.append(vx)
                all_ys.append(vy)
        lines.append("")

        # [LABELS]
        lines.append("[LABELS]")
        lines.append("")

        # [BACKDROP]
        if all_xs and all_ys:
            minx = min(all_xs) - self.backdrop_margin
            miny = min(all_ys) - self.backdrop_margin
            maxx = max(all_xs) + self.backdrop_margin
            maxy = max(all_ys) + self.backdrop_margin
        else:
            minx, miny, maxx, maxy = 0.0, 0.0, 1000.0, 1000.0

        lines.append("[BACKDROP]")
        lines.append(f" DIMENSIONS     {minx:.2f}    {miny:.2f}    {maxx:.2f}    {maxy:.2f}")
        lines.append(" UNITS          Meters")
        lines.append("")

        # [END]
        lines.append("[END]")
        lines.append("")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True
