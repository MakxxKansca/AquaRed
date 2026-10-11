"""
AquaRed - Diálogo de Ayuda Técnica y Normativa IDAAN
===================================================
Proporciona al usuario la documentación técnica, bases de diseño, fórmulas
del método de reparto por tramo IDAAN y la guía operativa paso a paso.
"""

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QTextBrowser,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt

class AquaRedHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AquaRed - Guía Técnica y Normativa IDAAN")
        self.resize(750, 550)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # TAB 1: Normativa IDAAN vs MINSA
        browser_norma = QTextBrowser()
        browser_norma.setHtml("""
        <h2>Normativa de Diseño de Acueductos en Panamá</h2>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%;">
            <tr style="background-color:#e6f2ff;">
                <th>Parámetro de Diseño</th>
                <th>Zona Urbana (Norma IDAAN)</th>
                <th>Zona Rural (Norma MINSA / IDAAN)</th>
            </tr>
            <tr>
                <td><b>Dotación de Consumo</b></td>
                <td>100 gal/hab/día (378.54 L/hab/día)</td>
                <td>80 gal/hab/día (302.83 L/hab/día)</td>
            </tr>
            <tr>
                <td><b>Presión Mínima Dinámica</b></td>
                <td>20.0 psi (14.06 m.c.a.)</td>
                <td>14.0 psi (10.00 m.c.a. / 9.84 mca)</td>
            </tr>
            <tr>
                <td><b>Presión Máxima Estática</b></td>
                <td>50.0 m.c.a.</td>
                <td>50.0 m.c.a.</td>
            </tr>
            <tr>
                <td><b>Diámetro Mínimo Troncal</b></td>
                <td>4 pulgadas (114.3 mm ext / 105.5 mm int)</td>
                <td>3 pulgadas (88.9 mm ext / 82.1 mm int)</td>
            </tr>
            <tr>
                <td><b>Diámetro Mínimo Ramales</b></td>
                <td>3 pulgadas (88.9 mm ext / 82.1 mm int)</td>
                <td>2 pulgadas (60.3 mm ext / 55.7 mm int)</td>
            </tr>
            <tr>
                <td><b>Factor Caudal Máximo Horario</b></td>
                <td>FMH = 2.00</td>
                <td>Kp = K1 * K2 = 1.2 * 1.8 = 2.16</td>
            </tr>
            <tr>
                <td><b>Densidad Habitacional</b></td>
                <td>5 habitantes / vivienda</td>
                <td>5 habitantes / vivienda</td>
            </tr>
            <tr>
                <td><b>Profundidad de Zanja</b></td>
                <td>1.15 m (Cama de arena + relleno compactado)</td>
                <td>1.10 m</td>
            </tr>
        </table>
        """)
        tabs.addTab(browser_norma, "Normativa y Criterios")

        # TAB 2: Método Oficial de Tramo IDAAN
        browser_metodo = QTextBrowser()
        browser_metodo.setHtml("""
        <h2>Método Oficial de Asignación por Tramo (Script 15)</h2>
        <p>Para redes de distribución ramificadas o malladas, la norma oficial del IDAAN no modela micro-nodos en cada toma individual, sino que realiza un reparto biseccional por tramo matriz:</p>
        <ol>
            <li><b>Cálculo del Caudal de Diseño por Tramo:</b><br>
                Cada tramo de tubería contabiliza el número total de viviendas (<i>N<sub>casas</sub></i>) cuyas acometidas derivan de él:<br>
                <div style="background-color:#f4f4f4; padding:8px; border-left:4px solid #007acc; font-family:monospace;">
                Habitantes = N<sub>casas</sub> &times; 5 hab/casa<br>
                Q<sub>medio</sub> (L/s) = (Habitantes &times; Dotación<sub>L</sub>) / 86400<br>
                Q<sub>diseño</sub> (L/s) = Q<sub>medio</sub> &times; FMH
                </div>
            </li>
            <br>
            <li><b>Reparto Biseccional (50% - 50%):</b><br>
                El caudal de diseño del tramo se distribuye equitativamente entre sus dos nodos extremos:<br>
                <b>Aporte a Nodo Inicial:</b> 50% de Q<sub>diseño</sub><br>
                <b>Aporte a Nodo Final:</b> 50% de Q<sub>diseño</sub>
            </li>
            <br>
            <li><b>Demanda Nodal Final:</b><br>
                La demanda de base ingresada a cada nodo de la red en EPANET corresponde exactamente a la <b>suma de las mitades de todos los tramos que confluyen en él</b>.
            </li>
            <br>
            <li><b>Garantía de Balance de Masa:</b><br>
                La suma de todas las demandas nodales equivale matemáticamente al <b>100.00%</b> del caudal de diseño del acueducto (0.00% error).
            </li>
        </ol>
        """)
        tabs.addTab(browser_metodo, "Asignación IDAAN")

        # TAB 3: Capas del Proyecto
        browser_capas = QTextBrowser()
        browser_capas.setHtml("""
        <h2>Insumos y Capas del Proyecto (Panel 2)</h2>
        <p>AquaRed interactúa dinámicamente con las capas cargadas en el panel lateral de <b>Capas</b> de QGIS mediante controles inteligentes (<code>QgsMapLayerComboBox</code>):</p>
        
        <div style="background-color:#eef7ff; padding:10px; border-left:4px solid #007acc; margin-bottom:12px;">
            <b>¿Por qué los desplegables aparecen vacíos al inicio?</b><br>
            Si tu proyecto de QGIS está en blanco o recién iniciado, los menús no muestran opciones. Tan pronto arrastres o abras tus archivos (<code>.shp</code>, <code>.gpkg</code>, <code>.geojson</code>, <code>.tif</code>) en QGIS, AquaRed detectará automáticamente la geometría de cada capa y la listará en el desplegable correspondiente.
        </div>

        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%;">
            <tr style="background-color:#e6f2ff;">
                <th>Campo en Panel</th>
                <th>Tipo de Geometría</th>
                <th>Función en el Diseño</th>
            </tr>
            <tr>
                <td><b>Ejes Viales / Calles</b></td>
                <td>Líneas (<code>LineString</code>)</td>
                <td>Ejes viales base (descargados de OSM o trazados en CAD). Directriz para calcular las tuberías principales con offset paralelo (ej. 5.0 m).</td>
            </tr>
            <tr>
                <td><b>Viviendas / Huellas</b></td>
                <td>Puntos o Polígonos (<code>Point</code> / <code>Polygon</code>)</td>
                <td>Ubicación de lotes o casas. Permite trazar las acometidas de 1/2" y calcular la población tributaria y caudal de diseño por tramo (IDAAN).</td>
            </tr>
            <tr>
                <td><b>Ráster DEM</b></td>
                <td>Ráster de Elevación (<code>.tif</code>)</td>
                <td>MDT topográfico. Permite muestrear la cota de terreno (<code>cota_terreno</code>) y la cota de fondo de zanja (<code>cota_tubo</code>) de cada nodo.</td>
            </tr>
            <tr>
                <td><b>Tanque / Fuente</b></td>
                <td>Puntos (<code>Point</code>)</td>
                <td>Ubicación del tanque de reserva o fuente (nodo <code>TK-001</code>). Define la cota de terreno + altura de torre para la carga hidráulica total en EPANET.</td>
            </tr>
        </table>

        <h3>Recomendación Técnica:</h3>
        <p>Todas las capas deben estar en el mismo <b>Sistema de Coordenadas Proyectado (Métrico)</b>, por ejemplo <b>UTM WGS 84</b> (ej. <i>EPSG:32617</i> para Panamá), para garantizar que las distancias, offsets y cotas se calculen en metros exactos.</p>
        """)
        tabs.addTab(browser_capas, "Capas del Proyecto")

        # TAB 4: Offset Vial y Topología
        browser_offset = QTextBrowser()
        browser_offset.setHtml("""
        <h2>Trazado con Offset Vial y Topología Continua</h2>
        <ul>
            <li><b>Preservación de Ejes Viales:</b> Los ejes de las calles descargados de OpenStreetMap o provistos por el usuario nunca se modifican (diferencia = 0.00 m).</li>
            <li><b>Offset Paralelo Continuo:</b> La tubería se genera desplazada 5.0 metros (o el valor fijado) mediante curvas paralelas que conservan todas las curvas y quiebres reales de las calles.</li>
            <li><b>Acera Interior:</b> El plugin evalúa automáticamente el límite del proyecto para disponer la tubería en la acera interior de la urbanización, evitando cruces innecesarios de calzada.</li>
            <li><b>Auto-Snapping Topológico:</b> Los nodos Tee y derivaciones se recortan en las intersecciones exactas de las curvas de offset para eliminar quiebres agudos retrógrados.</li>
        </ul>
        """)
        tabs.addTab(browser_offset, "Offset y Geometría")

        # TAB 5: Exportación EPANET
        browser_epanet = QTextBrowser()
        browser_epanet.setHtml("""
        <h2>Exportación a EPANET (.INP)</h2>
        <ul>
            <li><b>Autocontenido:</b> El plugin genera el archivo .INP nativamente sin requerir bibliotecas pesadas de terceros.</li>
            <li><b>Sección [VERTICES]:</b> Exporta todos los vértices de curvatura para que la red se visualice en EPANET con la misma geometría que en QGIS.</li>
            <li><b>Sección [BACKDROP]:</b> Configura automáticamente el encuadre espacial con las coordenadas UTM exactas de la red.</li>
            <li><b>Modulación Horaria:</b> Incluye el patrón horario diario de 24 horas normalizado con coeficiente 1.000 a la hora de consumo pico (06:00 AM).</li>
        </ul>
        """)
        tabs.addTab(browser_epanet, "Exportación EPANET")

        # TAB 6: Personalización de Perfiles JSON
        browser_json = QTextBrowser()
        browser_json.setHtml("""
        <h2>Guía de Personalización de Perfiles JSON</h2>
        <p>AquaRed permite guardar y cargar configuraciones completas de diseño mediante archivos <b>.json</b> portables. Esto permite reutilizar parámetros en proyectos similares o adaptarlos a normativas de otros países.</p>
        
        <h3>1. ¿Cómo crear y cargar un perfil JSON?</h3>
        <ul>
            <li><b>Desde la Interfaz Gráfica:</b> Modifica los valores en el panel lateral (dotación, offset, zanja, diámetros, etc.) y pulsa el botón <b>💾 Guardar JSON</b>. Para reutilizarlo en otro proyecto, pulsa <b>📂 Cargar JSON</b>.</li>
            <li><b>Editando el archivo manualmente:</b> Puedes crear un archivo <code>mi_perfil.json</code> con cualquier editor de texto (Notepad, VSCode) respetando la estructura de claves descrita abajo.</li>
        </ul>

        <h3>2. Diccionario de Claves del Archivo JSON</h3>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%;">
            <tr style="background-color:#e6f2ff;">
                <th>Clave JSON</th>
                <th>Tipo</th>
                <th>Descripción y Rango / Opciones</th>
            </tr>
            <tr>
                <td><code>nombre_perfil</code></td>
                <td>Texto</td>
                <td>Nombre que se mostrará en el menú desplegable del plugin.</td>
            </tr>
            <tr>
                <td><code>clasificacion</code></td>
                <td>Texto</td>
                <td><code>"urbano"</code> o <code>"rural"</code>. Define la base normativa.</td>
            </tr>
            <tr>
                <td><code>dotacion_gal_hab_dia</code></td>
                <td>Número</td>
                <td>Consumo por habitante al día en galones (ej. 100.0, 80.0, 120.0).</td>
            </tr>
            <tr>
                <td><code>presion_min_psi</code></td>
                <td>Número</td>
                <td>Presión mínima dinámica requerida en psi (ej. 20.0, 14.0).</td>
            </tr>
            <tr>
                <td><code>diam_min_troncal</code></td>
                <td>Texto</td>
                <td>Diámetro mínimo para tubería principal (<code>"4\""</code>, <code>"3\""</code>, etc.).</td>
            </tr>
            <tr>
                <td><code>diam_min_ramal</code></td>
                <td>Texto</td>
                <td>Diámetro mínimo para ramales secundarios (<code>"3\""</code>, <code>"2\""</code>, etc.).</td>
            </tr>
            <tr>
                <td><code>factor_pico_fmh</code></td>
                <td>Número</td>
                <td>Factor de caudal máximo horario (ej. 2.00 para urbano, 2.16 para rural).</td>
            </tr>
            <tr>
                <td><code>hab_por_vivienda</code></td>
                <td>Número</td>
                <td>Densidad habitacional (habitualmente 5.0 habitantes por vivienda).</td>
            </tr>
            <tr>
                <td><code>offset_tuberias_m</code></td>
                <td>Número</td>
                <td>Desplazamiento paralelo en metros respecto al eje de calle (ej. 5.00, 4.00, 3.00).</td>
            </tr>
            <tr>
                <td><code>profundidad_zanja_m</code></td>
                <td>Número</td>
                <td>Profundidad de excavación al lomo/batea del tubo en metros (ej. 1.15, 1.10).</td>
            </tr>
            <tr>
                <td><code>altura_torre_tanque_m</code></td>
                <td>Número</td>
                <td>Altura de la torre del tanque elevado en metros (ej. 15.00, 10.00).</td>
            </tr>
            <tr>
                <td><code>tolerancia_snapping_m</code></td>
                <td>Número</td>
                <td>Tolerancia de auto-ensamblado en metros para unir vértices (ej. 0.75, 0.50).</td>
            </tr>
            <tr>
                <td><code>umbral_acometida_m</code></td>
                <td>Número</td>
                <td>Distancia máxima admisible para conectar una casa a la tubería (ej. 25.0, 30.0).</td>
            </tr>
        </table>

        <h3>3. Ejemplo de Archivo JSON Completo</h3>
        <pre style="background-color:#f4f4f4; padding:10px; border-radius:4px; font-size:11px;">
{
    "nombre_perfil": "Acueducto Urbano 100 gal",
    "clasificacion": "urbano",
    "dotacion_gal_hab_dia": 100.0,
    "presion_min_psi": 20.0,
    "diam_min_troncal": "4\"",
    "diam_min_ramal": "3\"",
    "factor_pico_fmh": 2.00,
    "hab_por_vivienda": 5.0,
    "offset_tuberias_m": 5.00,
    "profundidad_zanja_m": 1.15,
    "altura_torre_tanque_m": 15.00,
    "tolerancia_snapping_m": 0.75,
    "umbral_acometida_m": 25.0
}
        </pre>
        """)
        tabs.addTab(browser_json, "Personalización JSON")

        layout.addWidget(tabs)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)
