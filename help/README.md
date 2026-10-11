# AquaRed - QGIS Plugin

**Diseñador y Modelador Topológico de Redes de Agua Potable con Offset Vial, Acometidas, Normativa IDAAN y Exportación a EPANET**

---

## 📌 Descripción General

**AquaRed** es un plugin integral para QGIS (versiones 3.22 a 3.99) diseñado para automatizar el diseño técnico, la estructuración topológica y el modelado hidráulico de redes de distribución de agua potable según la normativa oficial de Panamá (**IDAAN** para zonas urbanas y **MINSA / IDAAN Rural** para comunidades rurales).

---

## 🚀 Características Principales

1. **Extracción y Preparación de Calles y Viviendas:**
   - Descarga directa desde OpenStreetMap mediante Overpass API o utilización de capas locales del proyecto.
   - Centroides y áreas de viviendas calculadas automáticamente.

2. **Muestreo de Elevaciones desde Ráster DEM:**
   - Asigna cotas topográficas (`cota_terreno`) y cotas de zanja (`cota_tubo`) en base a un modelo digital de elevación.

3. **Trazado de Tuberías con Offset Paralelo Exclusivo:**
   - Genera tuberías paralelas a una distancia configurable (e.g. 5.0 m) preservando el 100% de la geometría y curvatura de las calles.
   - Mantiene los ejes viales originales intactos (diferencia de 0.00 m).
   - Detección automática del lado interior de la calzada para minimizar cruces de vía.

4. **Trazado Perpendicular de Acometidas Domiciliarias:**
   - Conecta cada vivienda de forma perpendicular a su tubería matriz más cercana con diámetros de 1/2" (PEAD SDR-11 / PVC).

5. **Asignación Oficial de Demandas por Método de Tramo IDAAN (Script 15):**
   - Agrupa viviendas por tramo matriz.
   - Aplica dotación (100 gal/hab/día urbano vs 80 gal/hab/día rural) y factores pico de caudal máximo horario.
   - Reparto biseccional 50% al nodo aguas arriba y 50% al nodo aguas abajo.
   - Demanda nodal acumulada como suma algebraica de aportes de tramos concurrentes.
   - Garantía de balance de masa del 100.00% (cero error de balance).

6. **Validación Topológica de Grafo y Accesorios Técnicos:**
   - Verifica que la red sea 100% conexa (1 solo componente conexo en grafo).
   - Genera compuertas de aislamiento de cabecera, ventosas trifuncionales en puntos altos y purgas en fondos de saco.

7. **Exportación Nativa a EPANET (.INP):**
   - Totalmente autocontenido (sin dependencias de librerías externas).
   - Incluye secciones `[JUNCTIONS]`, `[RESERVOIRS]`, `[PIPES]`, `[PATTERNS]`, `[COORDINATES]`, `[VERTICES]` y encuadre `[BACKDROP]` con coordenadas UTM.

8. **Asistente de Auto-Snapping y Edición Topológica:**
   - Configura con un solo clic el auto-ensamblado en vértices, segmentos e intersecciones del proyecto activo de QGIS.

---

## 📦 Instalación

1. **Instalación Manual:**
   - Copiar la carpeta `AquaRed` en el directorio de plugins de QGIS:
     - En Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\AquaRed`
   - O bien, desde QGIS: `Complementos` -> `Administrar e instalar complementos` -> `Instalar a partir de ZIP` -> Seleccionar `AquaRed.zip`.
2. Reiniciar QGIS o recargar complementos.
3. Activar la casilla de verificación **AquaRed**.
4. El plugin añadirá un botón en la barra de herramientas y un panel lateral acoplable (`AquaRed Dock`).

---

## ⚙️ Parámetros Normativos Integrados

| Parámetro | Zona Urbana (IDAAN) | Zona Rural (MINSA) |
| :--- | :--- | :--- |
| **Dotación** | 100 gal/hab/día (378.54 L/hab/día) | 80 gal/hab/día (302.83 L/hab/día) |
| **Presión Mínima** | 20.0 psi (14.06 m.c.a.) | 14.0 psi (10.00 m.c.a.) |
| **Presión Máxima** | 50.0 m.c.a. | 50.0 m.c.a. |
| **Diámetro Mín. Troncal** | 4 pulgadas (105.5 mm int) | 3 pulgadas (82.1 mm int) |
| **Diámetro Mín. Ramal** | 3 pulgadas (82.1 mm int) | 2 pulgadas (55.7 mm int) |
| **Factor Caudal Máx. Horario** | FMH = 2.00 | Kp = 2.16 |
| **Rugosidad (C Hazen-Williams)**| 140 (PVC SDR-26) | 140 (PVC SDR-26) |

---

## 📝 Personalización de Perfiles JSON

AquaRed permite guardar y cargar configuraciones completas de diseño mediante archivos `.json` portables:
- **Desde la Interfaz:** Modifica los valores en el panel y pulsa **💾 Guardar JSON**. Para volver a usarlo, pulsa **📂 Cargar JSON**.
- **Editando el archivo manualmente:** Puedes modificar los campos de [`perfil_plantilla.json`](../perfil_plantilla.json) con cualquier editor de texto.

### Parámetros del Archivo JSON
- `nombre_perfil`: Nombre visible en la lista desplegable.
- `clasificacion`: `"urbano"` o `"rural"`.
- `dotacion_gal_hab_dia`: Consumo por habitante al día (ej. 100.0, 80.0, 120.0).
- `presion_min_psi`: Presión mínima dinámica en psi (ej. 20.0, 14.0).
- `diam_min_troncal`: Diámetro mínimo de la tubería principal (ej. `"4\""`, `"3\""`).
- `diam_min_ramal`: Diámetro mínimo de ramales secundarios (ej. `"3\""`, `"2\""`).
- `factor_pico_fmh`: Factor de caudal máximo horario (ej. 2.00, 2.16).
- `hab_por_vivienda`: Densidad habitacional (ej. 5.0).
- `offset_tuberias_m`: Distancia de offset en metros respecto al eje vial (ej. 5.00, 4.00).
- `profundidad_zanja_m`: Profundidad de excavación en metros (ej. 1.15, 1.10).
- `altura_torre_tanque_m`: Altura de torre del tanque elevado en metros (ej. 15.00).
- `tolerancia_snapping_m`: Tolerancia de auto-ensamblado en metros (ej. 0.75).
- `umbral_acometida_m`: Distancia máxima para buscar la tubería más cercana (ej. 25.0).

---

## 👤 Autor

- **Autor:** **MakxxKansca**
- **GitHub:** [@MakxxKansca](https://github.com/MakxxKansca)

---

## 📄 Licencia

Este software está protegido por derechos de autor y se distribuye bajo **Licencia Propietaria de Uso Gratuito (Freeware)**. Todos los derechos reservados por MakxxKansca. Queda prohibida la copia, modificación o redistribución no autorizada del código fuente.
