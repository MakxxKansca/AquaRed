# AquaRed - Plugin de QGIS

**Diseñador y Modelador Topológico de Redes de Agua Potable con Offset Vial, Acometidas Domiciliarias, Normativa Oficial IDAAN / MINSA y Exportación Nativa a EPANET (.INP)**

![AquaRed Icon](icon.png)

[![QGIS Version](https://img.shields.io/badge/QGIS-3.22%20--%203.99-brightgreen.svg)](https://qgis.org/)
[![License: Proprietary / Freeware](https://img.shields.io/badge/License-Proprietary%20%2F%20Freeware-red.svg)](LICENSE)
[![Author](https://img.shields.io/badge/Author-MakxxKansca-orange.svg)](https://github.com/MakxxKansca)
[![Issues](https://img.shields.io/github/issues/MakxxKansca/AquaRed)](https://github.com/MakxxKansca/AquaRed/issues)

---

## 📌 Descripción General

**AquaRed** es un complemento profesional para **QGIS** desarrollado para automatizar el diseño técnico, la estructuración topológica y el modelado hidráulico de redes de distribución de agua potable según la normativa oficial de la República de Panamá:
- **Norma IDAAN** para zonas urbanas.
- **Norma MINSA / IDAAN Rural** para comunidades rurales.

Permite generar redes de tuberías matrices desplazadas a un offset paralelo configurable (p. ej. 5.0 m) conservando el 100% de la curvatura y los ejes viales originales intactos, trazar acometidas domiciliarias perpendiculares, repartir la demanda con el método oficial de tramo IDAAN (50%–50% con balance de masa perfecto) y exportar el modelo directamente a **EPANET** sin dependencias externas.

---

## 🚀 Capacidades Principales

1. **Extracción y Preparación de Calles y Viviendas:**
   - Descarga directa desde OpenStreetMap mediante Overpass API o selección de capas vectoriales locales del proyecto.
   - Centroides y huellas de viviendas calculadas automáticamente.

2. **Muestreo de Elevaciones desde Ráster DEM:**
   - Asigna cotas topográficas del terreno (`cota_terreno`) y cotas de zanja (`cota_tubo`) en base a un modelo digital de elevación.

3. **Trazado de Tuberías con Offset Paralelo Exclusivo:**
   - Aplica un desplazamiento paralelo continuo a los ejes viales preservando todas las curvas y quiebres reales.
   - Preserva los ejes viales originales con diferencia matemática = 0.00 m.
   - Evaluación automática de la acera interior de la urbanización para minimizar cruces de calzada.

4. **Trazado Perpendicular de Acometidas Domiciliarias:**
   - Conecta cada vivienda de forma perpendicular a su tubería matriz más cercana con tubería de 1/2" (PEAD SDR-11 / PVC).

5. **Asignación Oficial de Demandas por Método de Tramo IDAAN (Script 15):**
   - Agrupa viviendas por tramo matriz.
   - Aplica dotación (100 gal/hab/día urbano vs 80 gal/hab/día rural) y factor de caudal máximo horario.
   - Reparto biseccional: **50% al nodo aguas arriba y 50% al nodo aguas abajo**.
   - Demanda nodal acumulada como suma algebraica de aportes de tramos concurrentes.
   - **Garantía de balance de masa del 100.00%** (cero error de balance).

6. **Validación Topológica de Grafo y Accesorios Técnicos:**
   - Verifica que la red sea 100% conexa (1 solo componente conexo en grafo).
   - Genera compuertas de aislamiento de cabecera, ventosas trifuncionales en puntos altos y purgas en fondos de saco.

7. **Exportación Nativa a EPANET (.INP):**
   - Totalmente autocontenido (sin requerir WNTR ni librerías pesadas en tiempo de ejecución).
   - Soporte para secciones `[JUNCTIONS]`, `[RESERVOIRS]`, `[PIPES]`, `[PATTERNS]` (24 horas normalizado con pico a las 06:00 AM), `[COORDINATES]` (UTM), `[VERTICES]` (preservación de curvatura idéntica a QGIS) y `[BACKDROP]`.

8. **Asistente de Auto-Snapping y Edición Topológica:**
   - Configura con un solo clic el auto-ensamblado en vértices, segmentos e intersecciones del proyecto activo de QGIS.

---

## ⚙️ Criterios Normativos Integrados

| Parámetro | Zona Urbana (IDAAN) | Zona Rural (MINSA / IDAAN Rural) |
| :--- | :--- | :--- |
| **Dotación de Consumo** | 100 gal/hab/día (378.54 L/hab/día) | 80 gal/hab/día (302.83 L/hab/día) |
| **Presión Mínima Dinámica** | 20.0 psi (14.06 m.c.a.) | 14.0 psi (10.00 m.c.a.) |
| **Presión Máxima Estática** | 50.0 m.c.a. | 50.0 m.c.a. |
| **Diámetro Mín. Troncal** | 4 pulgadas (105.5 mm int, PVC SDR-26) | 3 pulgadas (82.1 mm int, PVC SDR-26) |
| **Diámetro Mín. Ramal** | 3 pulgadas (82.1 mm int, PVC SDR-26) | 2 pulgadas (55.7 mm int, PVC SDR-26) |
| **Factor Caudal Máx. Horario** | FMH = 2.00 | Kp = K1(1.2) * K2(1.8) = 2.16 |
| **Rugosidad Hazen-Williams** | C = 140 | C = 140 |

---

## 📦 Instalación en QGIS

### Método 1: Descarga e Instalación Directa desde QGIS (Repositorio Personalizado)
Puedes hacer que **AquaRed** aparezca en el buscador de complementos de QGIS e instalarlo o actualizarlo con 1 solo clic:
1. En QGIS, ve a: `Complementos` $\rightarrow$ `Administrar e instalar complementos...`
2. En la pestaña izquierda, selecciona **Opciones**.
3. En la sección *Repositorios de complementos*, pulsa **Añadir**.
4. Completa los campos:
   - **Nombre:** `AquaRed Repository`
   - **URL:** `https://raw.githubusercontent.com/MakxxKansca/AquaRed/main/plugins.xml`
5. Pulsa **Aceptar**.
6. Ahora ve a la pestaña **Todos** o **No instalados**, busca **AquaRed** y pulsa **Instalar complemento**. ¡Recibirás notificaciones automáticas cada vez que se publique una nueva versión!

### Método 2: Instalación desde Archivo ZIP
1. Descarga el paquete [`AquaRed.zip`](https://raw.githubusercontent.com/MakxxKansca/AquaRed/main/AquaRed.zip).
2. En QGIS, ve a: `Complementos` $\rightarrow$ `Administrar e instalar complementos...` $\rightarrow$ `Instalar a partir de ZIP`.
3. Selecciona el archivo descargado y pulsa **Instalar complemento**.

### Método 3: Instalación Manual
Copia la carpeta `AquaRed` en el directorio de plugins de tu perfil de usuario de QGIS:
- **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\AquaRed`
- **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/AquaRed`
- **macOS:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/AquaRed`

---

## 🛠️ Estructura del Proyecto

```
AquaRed/
├── __init__.py                 # Punto de entrada classFactory(iface)
├── plugin.py                   # Ciclo de vida y barra de herramientas
├── metadata.txt                # Metadatos del plugin para el instalador QGIS
├── icon.png                    # Icono del plugin
├── README.md                   # Documentación principal
│
├── core/                       # Motores de cálculo independientes de la GUI
│   ├── idaan_rules.py          # Catálogo de tuberías y reglas de cálculo
│   ├── profile_manager.py      # Gestor de perfiles JSON (Red Urbana, Red Rural, Personalizado)
│   ├── topology_engine.py      # Geometría, offset, acometidas, grafo conexo y válvulas
│   └── epanet_exporter.py      # Generador nativo ASCII de archivos .INP
│
├── algorithms/                 # Procesos nativos para la Caja de Herramientas de QGIS
│   ├── provider.py             # AquaRed Processing Provider
│   ├── step1_extraer_base.py   # Paso 1: Extracción Overpass OSM o capas locales
│   ├── step2_dem_sampling.py   # Paso 2: Muestreo de elevaciones desde DEM
│   ├── step3_trazar_offset.py  # Paso 3: Trazado de tuberías con offset paralelo
│   ├── step4_acometidas.py     # Paso 4: Acometidas domiciliarias 1/2"
│   ├── step5_demandas_idaan.py # Paso 5: Asignación oficial por tramo IDAAN
│   ├── step6_validaciones.py   # Paso 6: Validación topológica y accesorios
│   └── step7_exportar_inp.py   # Paso 7: Exportación nativa a EPANET .INP
│
├── gui/                        # Interfaz gráfica de usuario en PyQt5
│   ├── dockwidget.py           # Panel acoplable interactivo con sincronización Urbano/Rural
│   └── snapping_manager.py     # Asistente de auto-snapping y edición topológica
│
└── help/                       # Diálogos y guías de ayuda técnica
    ├── help_dialog.py          # Diálogo con tablas normativas y fórmulas
    └── README.md
```

---

## 👤 Autor

- **Autor:** **MakxxKansca**
- **GitHub:** [@MakxxKansca](https://github.com/MakxxKansca)
- **Contacto:** makxx16@gmail.com

---

## 📄 Licencia y Términos de Uso

Este software se distribuye bajo **Licencia Propietaria de Uso Gratuito (Freeware)**. Todos los derechos reservados.
- **Uso Autorizado:** Se permite la instalación, ejecución y uso libre del complemento en QGIS para cualquier proyecto de diseño de acueductos (personal, profesional o académico).
- **Protección del Código Fuente:** Queda expresamente prohibida la copia, reproducción, modificación, ingeniería inversa, creación de obras derivadas o redistribución comercial del código fuente sin autorización previa por escrito del autor (**MakxxKansca**).

Para consultar los términos detallados, revisa el archivo [LICENSE](LICENSE).
