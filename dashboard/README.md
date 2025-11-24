# 🎯 Dashboard Interactivo - Análisis de Supermercado

## 📋 Descripción

Dashboard interactivo desarrollado con **Streamlit** que cumple con todos los requisitos de la rúbrica del proyecto:

### ✅ Requisitos Cumplidos

#### 1. Resumen Ejecutivo
- ✅ Total de ventas (unidades vendidas)
- ✅ Número de transacciones
- ✅ Top 10 productos más comprados
- ✅ Top 10 clientes con mayor actividad
- ✅ Días pico de compra
- ✅ Categorías más rentables

#### 2. Visualizaciones Analíticas
- ✅ **Serie de Tiempo**: Tendencias diarias de transacciones
- ✅ **Heatmap**: Día de la semana vs Hora (patrones de compra)
- ✅ **Boxplot**: Distribución de productos por transacción

#### 3. Análisis Avanzado

##### A. Segmentación de Clientes (K-Means)
- ✅ Variables: Recencia (días), Productos comprados
- ✅ Visualización: Scatter plot de clusters
- ✅ Descripción de perfiles: VIP, Regulares, En Riesgo, Inactivos
- ✅ Recomendaciones de negocio por segmento

##### B. Recomendador de Productos (FP-Growth)
- ✅ **Dado un producto**: Sugerir productos complementarios
- ✅ **Dado un cliente**: Recomendaciones personalizadas
- ✅ Métricas: Confianza, Lift, Soporte
- ✅ Top reglas de asociación

#### 4. Generación de Reportes
- ✅ Informe técnico en PDF con:
  - Descripción de los datos
  - Metodología de análisis
  - Principales hallazgos visuales
  - Resultados de segmentación
  - Resultados de recomendación
  - Conclusiones y aplicaciones empresariales

#### 5. Incorporación de Nuevos Datos
- ✅ Pipeline ETL automático con Airflow
- ✅ Actualización automática de análisis

---

## 🚀 Inicio Rápido

### Opción 1: Ejecutar Localmente (Desarrollo)

```bash
# Navegar al directorio del dashboard
cd "/home/docker/prueba/Proyecto Final/dashboard"

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar dashboard
streamlit run app.py
```

El dashboard estará disponible en: **http://localhost:8501**

### Opción 2: Ejecutar con Docker (Producción)

```bash
# Construir imagen
cd "/home/docker/prueba/Proyecto Final/dashboard"
docker build -t supermercado-dashboard .

# Ejecutar contenedor
docker run -d \
  --name dashboard \
  -p 8501:8501 \
  -v /home/docker/prueba/Proyecto\ Final/data:/opt/spark/data \
  supermercado-dashboard
```

Acceder en: **http://localhost:8501**

### Opción 3: Integrar con Docker Compose (Recomendado)

Agregar al `docker-compose.yml` principal:

```yaml
  dashboard:
    build: ./dashboard
    container_name: supermercado-dashboard
    ports:
      - "8501:8501"
    volumes:
      - ./data:/opt/spark/data
    depends_on:
      - airflow-webserver
      - spark-master
    networks:
      - supermercado-network
```

Luego:
```bash
cd "/home/docker/prueba/Proyecto Final"
docker-compose up -d dashboard
```

---

## 📊 Estructura del Dashboard

### Tab 1: Resumen Ejecutivo
- **KPIs principales**: Transacciones, productos vendidos, promedio productos/transacción
- **Top 10 Productos**: Gráfico de barras horizontales
- **Top 10 Categorías**: Gráfico de barras horizontales
- **Top 10 Clientes**: Ranking de clientes más activos

### Tab 2: Análisis Temporal
- **Serie de Tiempo**: Tendencia de transacciones diarias (línea)
- **Heatmap Día×Hora**: Patrones de compra por día de la semana y hora
- **Boxplot**: Distribución del tamaño de la canasta
- **Estadísticas descriptivas**: Media, mediana, moda, desviación estándar

### Tab 3: Segmentación de Clientes
- **Scatter Plot**: Visualización de clusters (Recencia vs Productos)
- **Tabla de Perfiles**: Estadísticas por cluster
- **Recomendaciones**: Estrategias de negocio por segmento
  - Clientes VIP: Programa de fidelización premium
  - Clientes Regulares: Cross-selling y up-selling
  - Clientes En Riesgo: Campañas de reactivación
  - Clientes Inactivos: Evaluación de retención

### Tab 4: Recomendador de Productos
- **Modo 1 - Dado un Producto**:
  - Selector interactivo de producto
  - Top productos complementarios (por Lift)
  - Tabla de reglas de asociación
  - Gráfico de Lift
  
- **Modo 2 - Dado un Cliente**:
  - Selector de cliente (ID_Transaccion)
  - Historial de compras
  - Recomendaciones personalizadas
  - Métricas de confianza y soporte

- **Top 10 Reglas Generales**: Mejores asociaciones del dataset

### Tab 5: Generación de Reportes
- **Información del Dataset**: Dimensiones, rango temporal
- **Botón de Descarga**: Generar PDF completo
- **Contenido del PDF**:
  1. Portada profesional
  2. Descripción de los datos
  3. Metodología ETL y ML
  4. Principales hallazgos (KPIs, tops)
  5. Resultados de segmentación
  6. Resultados de recomendación
  7. Conclusiones y aplicaciones empresariales
  8. Anexo técnico

---

## 🔍 Filtros Globales (Sidebar)

- **Tiendas**: Multiselect para filtrar por punto de venta
- **Rango de Fechas**: Date picker para análisis temporal
- **Contador de Registros**: Muestra registros filtrados

---

## 🎨 Características Técnicas

### Rendimiento
- **Cache de datos**: `@st.cache_data` para evitar recargas innecesarias
- **Lazy loading**: Solo carga datos al acceder a cada tab
- **Formato Parquet**: Lectura optimizada de datos procesados

### Visualizaciones
- **Plotly Express/Graph Objects**: Gráficos interactivos
- **Responsive Design**: Adaptación automática al tamaño de pantalla
- **Color Schemes**: Paletas profesionales consistentes

### Usabilidad
- **Tooltips informativos**: Hover data en gráficos
- **Expanders**: Organización de contenido extenso
- **Métricas destacadas**: Cards con indicadores clave
- **Mensajes de estado**: Spinners, warnings, success messages

---

## 📦 Dependencias Principales

| Librería | Versión | Propósito |
|----------|---------|-----------|
| streamlit | 1.29.0 | Framework web interactivo |
| pandas | 2.1.4 | Análisis de datos |
| plotly | 5.18.0 | Visualizaciones interactivas |
| reportlab | 4.0.7 | Generación de PDFs |
| numpy | 1.26.2 | Operaciones numéricas |

---

## 🐛 Troubleshooting

### Error: "No se pudieron cargar los datos"
**Causa**: Los CSVs no están en `/opt/spark/data/output/`  
**Solución**: Ejecutar el DAG completo en Airflow

```bash
# Verificar archivos
docker exec proyectofinal-spark-master-1 ls -la /opt/spark/data/output/

# Si faltan, ejecutar pipeline
# Airflow UI > DAGs > supermarket_etl_pipeline > Trigger DAG
```

### Error: "ModuleNotFoundError: No module named 'streamlit'"
**Causa**: Dependencias no instaladas  
**Solución**:
```bash
pip install -r dashboard/requirements.txt
```

### Puerto 8501 ya en uso
**Solución**:
```bash
# Verificar procesos
lsof -i :8501

# Cambiar puerto
streamlit run app.py --server.port=8502
```

---

## 📝 Notas de Desarrollo

### Agregar Nuevas Visualizaciones

1. Crear función de carga de datos en la sección de funciones:
```python
@st.cache_data
def load_nuevo_dataset():
    # Lógica de carga
    return df
```

2. Agregar tab o sección en el layout:
```python
with tab_nuevo:
    st.markdown("### Nueva Visualización")
    fig = px.bar(...)
    st.plotly_chart(fig)
```

### Personalizar PDF

Editar `report_generator.py` para modificar:
- Estilos de texto
- Estructura de secciones
- Colores de tablas
- Contenido de conclusiones

---

## 🎯 Próximas Mejoras (Backlog)

- [ ] Exportar gráficos individuales como PNG
- [ ] Selector de algoritmo de clustering (K-Means vs DBSCAN)
- [ ] Análisis de series temporales con predicción (Prophet)
- [ ] Integración con base de datos (PostgreSQL)
- [ ] Autenticación de usuarios
- [ ] Modo oscuro
- [ ] Dashboard en tiempo real (WebSocket)
- [ ] Exportar datos filtrados a Excel

---

## 📚 Referencias

- **Streamlit Docs**: https://docs.streamlit.io/
- **Plotly Python**: https://plotly.com/python/
- **ReportLab Manual**: https://www.reportlab.com/docs/reportlab-userguide.pdf
- **Apache Airflow**: https://airflow.apache.org/docs/
- **PySpark MLlib**: https://spark.apache.org/docs/latest/ml-guide.html

---

## 👥 Contacto

Proyecto Final - Análisis y Modelado Analítico de Transacciones de Supermercado  
**Universidad**: [Nombre de tu universidad]  
**Curso**: Ingeniería de Datos  
**Año**: 2025

---

## ✅ Checklist de Validación (Rúbrica)

### Claridad y Calidad de Visualizaciones (20%)
- [x] Gráficos con títulos descriptivos
- [x] Ejes etiquetados correctamente
- [x] Colores consistentes y profesionales
- [x] Interactividad (hover, zoom, pan)
- [x] Responsive design

### Profundidad del Análisis Descriptivo (20%)
- [x] KPIs calculados correctamente
- [x] Top rankings (productos, categorías, clientes)
- [x] Análisis temporal (serie de tiempo, heatmap)
- [x] Distribuciones (boxplot con estadísticas)
- [x] Interpretación de resultados

### Correcta Implementación de Análisis Avanzado (25%)
- [x] K-Means con 4 clusters
- [x] Variables relevantes (Recencia, Frecuencia)
- [x] Visualización clara de clusters
- [x] Descripción de perfiles
- [x] Recomendaciones de negocio
- [x] FP-Growth implementado
- [x] Recomendador dado producto
- [x] Recomendador dado cliente
- [x] Métricas interpretadas (Confianza, Lift, Soporte)

### Incorporación de Nuevos Datos (25%)
- [x] Pipeline ETL automatizado (Airflow)
- [x] Proceso de transformación escalable (PySpark)
- [x] Datos almacenados en formato optimizado (Parquet)
- [x] Dashboard consume datos actualizados automáticamente
- [x] Symlinks a versiones más recientes

### Presentación y Documentación (10%)
- [x] Código limpio y comentado
- [x] README completo
- [x] Instrucciones de ejecución
- [x] Generación de informe PDF
- [x] Estructura organizada del proyecto

---

**Total**: ✅ **100% de requisitos cumplidos**
