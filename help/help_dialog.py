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

        # TAB 3: Offset Vial y Topología
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

        # TAB 4: Exportación EPANET
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

        layout.addWidget(tabs)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)
