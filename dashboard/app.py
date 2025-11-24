"""
Dashboard Interactivo - Análisis de Transacciones de Supermercado
Proyecto Final: Ingeniería de Datos

Cumple con requisitos de la rúbrica:
- Resumen Ejecutivo (KPIs y métricas)
- Visualizaciones Analíticas (serie tiempo, boxplot, heatmap)
- Análisis Avanzado (K-Means clustering, Recomendador)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Dashboard Supermercado - Análisis Avanzado",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Personalizado
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 20px 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 30px;
        margin-bottom: 15px;
        border-bottom: 3px solid #1f77b4;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================
# FUNCIONES DE CARGA DE DATOS
# ============================================================

@st.cache_data
def load_ventas_detalladas():
    """Cargar dataset de ventas detalladas"""
    try:
        # Intentar cargar archivo CSV directo primero
        csv_path = '/opt/spark/data/output/ventas_detalladas.csv'
        
        # Si es un archivo, leerlo directamente
        import os
        if os.path.isfile(csv_path):
            df = pd.read_csv(csv_path)
        else:
            # Si es directorio, buscar part-*.csv
            import glob
            csv_files = glob.glob(f'{csv_path}/part-*.csv')
            if not csv_files:
                st.error("❌ No se encontró el archivo de ventas detalladas")
                return None
            df = pd.read_csv(csv_files[0])
        
        # Convertir fecha
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        
        # Agregar columnas temporales adicionales
        df['Año_Mes'] = df['Fecha'].dt.to_period('M').astype(str)
        df['Nombre_Dia'] = df['Fecha'].dt.day_name()
        
        return df
    except Exception as e:
        st.error(f"Error cargando ventas: {e}")
        return None

@st.cache_data
def load_clusters():
    """Cargar datos de clustering"""
    try:
        csv_path = '/opt/spark/data/output/clientes_clusters.csv'
        
        import os
        if os.path.isfile(csv_path):
            df = pd.read_csv(csv_path)
        else:
            import glob
            csv_files = glob.glob(f'{csv_path}/part-*.csv')
            if not csv_files:
                st.warning("⚠️ Clusters no disponibles")
                return None
            df = pd.read_csv(csv_files[0])
        
        return df
    except Exception as e:
        st.warning(f"Clusters no disponibles: {e}")
        return None

@st.cache_data
def load_reglas():
    """Cargar reglas de asociación"""
    try:
        csv_path = '/opt/spark/data/output/reglas_asociacion.csv'
        
        import os
        if os.path.isfile(csv_path):
            df = pd.read_csv(csv_path)
        else:
            import glob
            csv_files = glob.glob(f'{csv_path}/part-*.csv')
            if not csv_files:
                st.warning("⚠️ Reglas no disponibles")
                return None
            df = pd.read_csv(csv_files[0])
        
        return df
    except Exception as e:
        st.warning(f"Reglas no disponibles: {e}")
        return None

@st.cache_data
def load_itemsets():
    """Cargar conjuntos frecuentes"""
    try:
        csv_path = '/opt/spark/data/output/conjuntos_frecuentes.csv'
        
        import os
        if os.path.isfile(csv_path):
            df = pd.read_csv(csv_path)
        else:
            import glob
            csv_files = glob.glob(f'{csv_path}/part-*.csv')
            if not csv_files:
                st.warning("⚠️ Itemsets no disponibles")
                return None
            df = pd.read_csv(csv_files[0])
        
        return df
    except Exception as e:
        st.warning(f"Itemsets no disponibles: {e}")
        return None

# ============================================================
# CARGAR TODOS LOS DATOS
# ============================================================

st.markdown('<div class="main-header">🛒 Dashboard de Análisis de Supermercado</div>', unsafe_allow_html=True)
st.markdown("---")

with st.spinner("🔄 Cargando datos del pipeline ETL..."):
    df_ventas = load_ventas_detalladas()
    df_clusters = load_clusters()
    df_reglas = load_reglas()
    df_itemsets = load_itemsets()

if df_ventas is None:
    st.error("❌ No se pudieron cargar los datos. Ejecuta el pipeline ETL primero.")
    st.stop()

# ============================================================
# SIDEBAR - FILTROS GLOBALES
# ============================================================

st.sidebar.header("🔍 Filtros")

# Filtro de tiendas
tiendas_disponibles = sorted(df_ventas['ID_Tienda'].unique())
tiendas_seleccionadas = st.sidebar.multiselect(
    "Tiendas:",
    options=tiendas_disponibles,
    default=tiendas_disponibles
)

# Filtro de fechas
fecha_min = df_ventas['Fecha'].min().date()
fecha_max = df_ventas['Fecha'].max().date()
fecha_inicio, fecha_fin = st.sidebar.date_input(
    "Rango de Fechas:",
    value=(fecha_min, fecha_max),
    min_value=fecha_min,
    max_value=fecha_max
)

# Aplicar filtros
df_filtrado = df_ventas[
    (df_ventas['ID_Tienda'].isin(tiendas_seleccionadas)) &
    (df_ventas['Fecha'].dt.date >= fecha_inicio) &
    (df_ventas['Fecha'].dt.date <= fecha_fin)
]

st.sidebar.markdown("---")
st.sidebar.info(f"📊 **Registros filtrados:** {len(df_filtrado):,}")

# ============================================================
# TABS PRINCIPALES
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Resumen Ejecutivo",
    "📈 Análisis Temporal",
    "👥 Segmentación de Clientes",
    "🔗 Recomendador de Productos",
    "📄 Generación de Reportes"
])

# ============================================================
# TAB 1: RESUMEN EJECUTIVO
# ============================================================

with tab1:
    st.markdown('<div class="section-header">📊 Indicadores Clave (KPIs)</div>', unsafe_allow_html=True)
    
    # Calcular KPIs
    total_transacciones = df_filtrado['ID_Transaccion'].nunique()
    total_productos_vendidos = len(df_filtrado)
    productos_unicos = df_filtrado['ID_Producto'].nunique()
    categorias_activas = df_filtrado['Nombre_Categoria'].nunique()
    promedio_productos_transaccion = total_productos_vendidos / total_transacciones if total_transacciones > 0 else 0
    
    # Mostrar KPIs en columnas
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="🛒 Total Transacciones",
            value=f"{total_transacciones:,}"
        )
    
    with col2:
        st.metric(
            label="📦 Productos Vendidos",
            value=f"{total_productos_vendidos:,}"
        )
    
    with col3:
        st.metric(
            label="🎯 Productos Únicos",
            value=f"{productos_unicos:,}"
        )
    
    with col4:
        st.metric(
            label="📂 Categorías Activas",
            value=f"{categorias_activas:,}"
        )
    
    with col5:
        st.metric(
            label="📊 Avg Productos/Transacción",
            value=f"{promedio_productos_transaccion:.2f}"
        )
    
    st.markdown("---")
    
    # BUSCADOR DE PRODUCTOS
    st.markdown("### 🔍 Consultar Categoría de Producto")
    col_buscar1, col_buscar2 = st.columns([1, 3])
    
    with col_buscar1:
        producto_id = st.number_input(
            "Ingrese ID del Producto",
            min_value=0,
            max_value=100,
            value=7,
            step=1
        )
    
    with col_buscar2:
        if producto_id > 0:
            producto_info = df_filtrado[df_filtrado['ID_Producto'] == producto_id]
            if not producto_info.empty:
                categoria = producto_info['Nombre_Categoria'].iloc[0]
                total_ventas = len(producto_info)
                st.success(f"**Producto {producto_id}** pertenece a la categoría: **{categoria}**")
                st.info(f"📊 Volumen total vendido (unidades): **{total_ventas:,}**")
            else:
                st.warning(f"⚠️ No se encontraron datos para el Producto {producto_id}")
    
    st.markdown("---")
    
    # Top 10 Productos: VOLUMEN vs POPULARIDAD
    st.markdown("### 🏆 Top 10 Productos - Análisis Dual")
    
    col_vol, col_pop = st.columns(2)
    
    with col_vol:
        st.markdown("#### 📦 Por Volumen de Unidades")
        st.caption("Mide la cantidad total de unidades vendidas (incluyendo compras múltiples)")
        
        # Volumen: contar todas las filas (value_counts)
        top_productos_volumen = df_filtrado['ID_Producto'].value_counts().head(10).reset_index()
        top_productos_volumen.columns = ['ID_Producto', 'Unidades_Vendidas']
        
        # Agregar categoría
        top_productos_volumen = top_productos_volumen.merge(
            df_filtrado[['ID_Producto', 'Nombre_Categoria']].drop_duplicates(),
            on='ID_Producto',
            how='left'
        )
        
        fig_vol = px.bar(
            top_productos_volumen,
            y='ID_Producto',
            x='Unidades_Vendidas',
            orientation='h',
            text='Unidades_Vendidas',
            color='Unidades_Vendidas',
            color_continuous_scale='Blues',
            hover_data=['Nombre_Categoria']
        )
        fig_vol.update_traces(
            texttemplate='%{text:,.0f}',
            textposition='outside',
            marker_line_color='rgb(8,48,107)',
            marker_line_width=1.5
        )
        fig_vol.update_layout(
            yaxis={'categoryorder': 'total ascending', 'title': 'Producto ID'},
            xaxis={'title': 'Unidades Vendidas'},
            showlegend=False,
            height=450,
            plot_bgcolor='rgba(240,242,246,0.5)',
            font=dict(size=12)
        )
        st.plotly_chart(fig_vol, use_container_width=True)
    
    with col_pop:
        st.markdown("#### 🎯 Por Popularidad (Alcance)")
        st.caption("Mide en cuántas transacciones diferentes apareció el producto")
        
        # Popularidad: contar transacciones únicas por producto
        top_productos_popularidad = df_filtrado.groupby('ID_Producto')['ID_Transaccion'].nunique().reset_index()
        top_productos_popularidad.columns = ['ID_Producto', 'Num_Transacciones']
        top_productos_popularidad = top_productos_popularidad.nlargest(10, 'Num_Transacciones')
        
        # Agregar categoría
        top_productos_popularidad = top_productos_popularidad.merge(
            df_filtrado[['ID_Producto', 'Nombre_Categoria']].drop_duplicates(),
            on='ID_Producto',
            how='left'
        )
        
        fig_pop = px.bar(
            top_productos_popularidad,
            y='ID_Producto',
            x='Num_Transacciones',
            orientation='h',
            text='Num_Transacciones',
            color='Num_Transacciones',
            color_continuous_scale='Greens',
            hover_data=['Nombre_Categoria']
        )
        fig_pop.update_traces(
            texttemplate='%{text:,.0f}',
            textposition='outside',
            marker_line_color='rgb(0,100,0)',
            marker_line_width=1.5
        )
        fig_pop.update_layout(
            yaxis={'categoryorder': 'total ascending', 'title': 'Producto ID'},
            xaxis={'title': 'Número de Transacciones'},
            showlegend=False,
            height=450,
            plot_bgcolor='rgba(240,242,246,0.5)',
            font=dict(size=12)
        )
        st.plotly_chart(fig_pop, use_container_width=True)
    
    # Explicación de la diferencia
    with st.expander("ℹ️ ¿Cuál es la diferencia entre Volumen y Popularidad?"):
        st.markdown("""
        **Volumen de Unidades**: Cuenta TODAS las unidades vendidas. Si una transacción incluye 3 unidades del Producto 7, 
        se cuentan las 3 unidades.
        
        **Popularidad (Alcance)**: Cuenta en cuántas TRANSACCIONES DIFERENTES apareció el producto. Si una transacción 
        tiene 3 unidades del Producto 7, cuenta como 1 sola transacción.
        
        **Ejemplo práctico**:
        - Producto A: Vendido en 1,000 transacciones, 5,000 unidades totales → Alta popularidad Y alto volumen
        - Producto B: Vendido en 100 transacciones, 5,000 unidades totales → Baja popularidad pero alto volumen (compras bulk)
        """)
    
    st.markdown("---")
    
    # Top 10 Categorías
    st.markdown("### 📂 Top 10 Categorías por Volumen de Ventas")
    
    top_categorias = df_filtrado['Nombre_Categoria'].value_counts().head(10).reset_index()
    top_categorias.columns = ['Categoría', 'Unidades_Vendidas']
    
    fig_categorias = px.bar(
        top_categorias,
        y='Categoría',
        x='Unidades_Vendidas',
        orientation='h',
        text='Unidades_Vendidas',
        color='Unidades_Vendidas',
        color_continuous_scale='Oranges'
    )
    fig_categorias.update_traces(
        texttemplate='%{text:,.0f}',
        textposition='outside',
        marker_line_color='rgb(139,69,19)',
        marker_line_width=1.5
    )
    fig_categorias.update_layout(
        yaxis={'categoryorder': 'total ascending', 'title': 'Categoría'},
        xaxis={'title': 'Unidades Vendidas'},
        showlegend=False,
        height=450,
        plot_bgcolor='rgba(240,242,246,0.5)',
        font=dict(size=12)
    )
    st.plotly_chart(fig_categorias, use_container_width=True)
    
    st.markdown("---")
    
    # Top 10 Transacciones Más Grandes
    st.markdown("### � Top 10 Transacciones Más Grandes")
    st.caption("Transacciones con mayor cantidad de productos comprados (no representa clientes, sino compras individuales grandes)")
    
    top_transacciones = df_filtrado.groupby('ID_Transaccion').agg({
        'ID_Producto': 'count',
        'Fecha': 'first',
        'ID_Tienda': 'first'
    }).reset_index()
    top_transacciones.columns = ['ID_Transaccion', 'Num_Productos', 'Fecha', 'Tienda']
    top_transacciones = top_transacciones.nlargest(10, 'Num_Productos')
    
    fig_trans = px.bar(
        top_transacciones,
        y='ID_Transaccion',
        x='Num_Productos',
        orientation='h',
        text='Num_Productos',
        color='Num_Productos',
        color_continuous_scale='Purples',
        hover_data=['Fecha', 'Tienda']
    )
    fig_trans.update_traces(
        texttemplate='%{text} productos',
        textposition='outside',
        marker_line_color='rgb(75,0,130)',
        marker_line_width=1.5
    )
    fig_trans.update_layout(
        yaxis={'categoryorder': 'total ascending', 'title': 'ID Transacción'},
        xaxis={'title': 'Cantidad de Productos'},
        showlegend=False,
        height=450,
        plot_bgcolor='rgba(240,242,246,0.5)',
        font=dict(size=12)
    )
    st.plotly_chart(fig_trans, use_container_width=True)
    
    with st.expander("ℹ️ Aclaración sobre 'Transacciones Más Grandes'"):
        st.markdown("""
        **Importante**: Este dataset NO contiene un ID de cliente. Por lo tanto, no podemos identificar clientes individuales.
        
        Lo que mostramos aquí son las **transacciones individuales más grandes**, es decir, compras únicas que incluyeron 
        muchos productos diferentes.
        
        **ID_Transaccion** representa una compra específica en un momento determinado, no la actividad acumulada de un cliente.
        """)


# ============================================================
# TAB 2: ANÁLISIS TEMPORAL
# ============================================================

with tab2:
    st.markdown('<div class="section-header">📈 Análisis Temporal</div>', unsafe_allow_html=True)
    
    # Serie de Tiempo: Transacciones por día
    st.markdown("### 📅 Serie de Tiempo: Transacciones por Día")
    
    transacciones_por_dia = df_filtrado.groupby('Fecha')['ID_Transaccion'].nunique().reset_index()
    transacciones_por_dia.columns = ['Fecha', 'Transacciones']
    
    fig_serie = px.line(
        transacciones_por_dia,
        x='Fecha',
        y='Transacciones',
        title="Tendencia de transacciones diarias",
        markers=True
    )
    fig_serie.update_layout(hovermode='x unified')
    st.plotly_chart(fig_serie, use_container_width=True)
    
    st.markdown("---")
    
    # Heatmap: Día de la Semana vs Hora
    st.markdown("### 🔥 Heatmap: Día de la Semana vs Hora")
    
    heatmap_data = df_filtrado.groupby(['DiaSemana', 'Hora']).size().reset_index(name='Cantidad')
    heatmap_pivot = heatmap_data.pivot(index='DiaSemana', columns='Hora', values='Cantidad').fillna(0)
    
    # Ordenar días de la semana (1=Domingo, 7=Sábado)
    dias_ordenados = [1, 2, 3, 4, 5, 6, 7]
    heatmap_pivot = heatmap_pivot.reindex(dias_ordenados, fill_value=0)
    
    fig_heatmap = px.imshow(
        heatmap_pivot,
        labels=dict(x="Hora del Día", y="Día de la Semana", color="Transacciones"),
        x=heatmap_pivot.columns,
        y=['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'],
        color_continuous_scale='YlOrRd',
        title="Patrones de compra por día y hora"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    st.markdown("---")
    
    # Boxplot: Distribución de productos por transacción
    st.markdown("### 📊 Boxplot: Distribución de Productos por Transacción")
    
    productos_por_transaccion = df_filtrado.groupby('ID_Transaccion').size().reset_index(name='Num_Productos')
    
    fig_boxplot = px.box(
        productos_por_transaccion,
        y='Num_Productos',
        title="Distribución del tamaño de la canasta",
        points='outliers'
    )
    st.plotly_chart(fig_boxplot, use_container_width=True)
    
    # Estadísticas descriptivas
    st.markdown("#### 📋 Estadísticas Descriptivas")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Media", f"{productos_por_transaccion['Num_Productos'].mean():.2f}")
    with col2:
        st.metric("Mediana", f"{productos_por_transaccion['Num_Productos'].median():.0f}")
    with col3:
        st.metric("Moda", f"{productos_por_transaccion['Num_Productos'].mode()[0]:.0f}")
    with col4:
        st.metric("Desv. Estándar", f"{productos_por_transaccion['Num_Productos'].std():.2f}")

# ============================================================
# TAB 3: SEGMENTACIÓN DE CLIENTES (K-MEANS)
# ============================================================

with tab3:
    st.markdown('<div class="section-header">👥 Segmentación de Clientes (K-Means)</div>', unsafe_allow_html=True)
    
    if df_clusters is not None:
        st.markdown("""
        **Metodología:** Segmentación realizada con K-Means usando variables:
        - **Recencia**: Días desde la última compra
        - **Frecuencia**: Número total de productos comprados
        """)
        
        st.markdown("---")
        
        # Scatter Plot de Clusters
        st.markdown("### 🎯 Visualización de Clusters")
        
        fig_clusters = px.scatter(
            df_clusters,
            x='Recencia_Dias',
            y='Productos_Comprados',
            color='Cluster',
            title="Segmentación de Clientes (K-Means)",
            labels={
                'Recencia_Dias': 'Recencia (días)',
                'Productos_Comprados': 'Productos Comprados',
                'Cluster': 'Cluster'
            },
            hover_data=['ID_Transaccion', 'ID_Tienda'],
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_clusters, use_container_width=True)
        
        st.markdown("---")
        
        # Descripción de cada Cluster
        st.markdown("### 📊 Perfil de Cada Segmento")
        
        cluster_stats = df_clusters.groupby('Cluster').agg({
            'ID_Transaccion': 'count',
            'Recencia_Dias': 'mean',
            'Productos_Comprados': 'mean'
        }).reset_index()
        cluster_stats.columns = ['Cluster', 'Num_Clientes', 'Recencia_Promedio', 'Productos_Promedio']
        
        st.dataframe(cluster_stats.style.format({
            'Recencia_Promedio': '{:.0f}',
            'Productos_Promedio': '{:.2f}'
        }), use_container_width=True)
        
        st.markdown("---")
        
        # Recomendaciones de Negocio
        st.markdown("### 💡 Recomendaciones de Negocio por Cluster")
        
        for idx, row in cluster_stats.iterrows():
            cluster_id = int(row['Cluster'])
            num_clientes = int(row['Num_Clientes'])
            recencia = row['Recencia_Promedio']
            productos = row['Productos_Promedio']
            
            with st.expander(f"**Cluster {cluster_id}** ({num_clientes:,} clientes)"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.metric("Recencia Promedio", f"{recencia:.0f} días")
                    st.metric("Productos Promedio", f"{productos:.2f}")
                
                with col2:
                    # Lógica de recomendaciones basada en perfil
                    if recencia < 3000 and productos > 20:
                        st.success("**🔥 Clientes VIP:** Alta frecuencia y recencia reciente")
                        st.write("- Ofrecer programa de fidelización premium")
                        st.write("- Enviar ofertas personalizadas exclusivas")
                    elif recencia < 3000 and productos <= 20:
                        st.info("**🌱 Clientes Regulares:** Potencial de crecimiento")
                        st.write("- Incentivar compras mediante cross-selling")
                        st.write("- Promociones en categorías complementarias")
                    elif recencia >= 3000 and productos > 20:
                        st.warning("**⚠️ Clientes en Riesgo:** Alta actividad histórica pero inactivos")
                        st.write("- Campaña de reactivación urgente")
                        st.write("- Descuentos especiales para recuperar")
                    else:
                        st.error("**💤 Clientes Inactivos:** Baja frecuencia y alta recencia")
                        st.write("- Evaluar costos de retención")
                        st.write("- Campañas genéricas de bajo costo")
        
    else:
        st.warning("⚠️ Los datos de clustering no están disponibles. Ejecuta el pipeline ETL completo.")

# ============================================================
# TAB 4: RECOMENDADOR DE PRODUCTOS
# ============================================================

with tab4:
    st.markdown('<div class="section-header">🔗 Recomendador de Productos (Market Basket)</div>', unsafe_allow_html=True)
    
    if df_reglas is not None and df_itemsets is not None:
        st.markdown("""
        **Algoritmo:** FP-Growth (Frequent Pattern Growth)
        
        Este recomendador identifica patrones de compra frecuentes y sugiere productos 
        que se compran juntos con alta probabilidad.
        """)
        
        st.markdown("---")
        
        # Selector de tipo de recomendación
        tipo_recomendacion = st.radio(
            "Selecciona el tipo de recomendación:",
            ["📦 Dado un Producto", "👤 Dado un Cliente"]
        )
        
        if tipo_recomendacion == "📦 Dado un Producto":
            st.markdown("### 🔍 Buscar Productos Complementarios")
            
            # Selector de producto
            productos_disponibles = sorted(df_itemsets['Productos'].unique())
            producto_seleccionado = st.selectbox(
                "Selecciona un producto:",
                options=productos_disponibles
            )
            
            if st.button("Generar Recomendación"):
                # Filtrar reglas donde el producto está en el antecedente
                reglas_filtradas = df_reglas[
                    df_reglas['Antecedente_Str'].str.contains(str(producto_seleccionado), na=False)
                ].sort_values('Lift', ascending=False).head(10)
                
                if len(reglas_filtradas) > 0:
                    st.success(f"✅ Se encontraron {len(reglas_filtradas)} recomendaciones")
                    
                    st.markdown("#### 🎯 Productos Recomendados")
                    st.dataframe(
                        reglas_filtradas[['Antecedente_Str', 'Consecuente_Str', 'Confianza', 'Lift', 'Soporte']]
                        .style.format({
                            'Confianza': '{:.2%}',
                            'Lift': '{:.2f}',
                            'Soporte': '{:.3f}'
                        }),
                        use_container_width=True
                    )
                    
                    # Gráfico de Lift
                    fig_lift = px.bar(
                        reglas_filtradas.head(5),
                        x='Lift',
                        y='Consecuente_Str',
                        orientation='h',
                        title="Top 5 Productos Complementarios (por Lift)",
                        color='Lift',
                        color_continuous_scale='Reds'
                    )
                    st.plotly_chart(fig_lift, use_container_width=True)
                else:
                    st.warning("⚠️ No se encontraron recomendaciones para este producto")
        
        else:  # Dado un Cliente
            st.markdown("### 👤 Recomendaciones Personalizadas por Cliente")
            
            # Selector de cliente (ID_Transaccion)
            clientes_disponibles = sorted(df_ventas['ID_Transaccion'].unique())
            cliente_seleccionado = st.selectbox(
                "Selecciona un cliente (ID_Transaccion):",
                options=clientes_disponibles[:100]  # Limitar a 100 para performance
            )
            
            if st.button("Generar Recomendación Personalizada"):
                # Obtener historial del cliente
                historial_cliente = df_ventas[
                    df_ventas['ID_Transaccion'] == cliente_seleccionado
                ]['ID_Producto'].unique()
                
                st.markdown(f"#### 🛒 Historial de Compras")
                st.write(f"El cliente ha comprado **{len(historial_cliente)} productos únicos**")
                st.write(f"Productos: {', '.join(map(str, historial_cliente[:10]))}" + 
                        ("..." if len(historial_cliente) > 10 else ""))
                
                # Encontrar productos recomendados
                recomendaciones = []
                for producto in historial_cliente:
                    reglas_aplicables = df_reglas[
                        df_reglas['Antecedente_Str'].str.contains(str(producto), na=False)
                    ]
                    recomendaciones.append(reglas_aplicables)
                
                if recomendaciones:
                    df_recomendaciones = pd.concat(recomendaciones).drop_duplicates()
                    df_recomendaciones = df_recomendaciones.sort_values('Lift', ascending=False).head(10)
                    
                    st.markdown("#### 🎁 Productos Sugeridos")
                    st.dataframe(
                        df_recomendaciones[['Consecuente_Str', 'Confianza', 'Lift', 'Soporte']]
                        .style.format({
                            'Confianza': '{:.2%}',
                            'Lift': '{:.2f}',
                            'Soporte': '{:.3f}'
                        }),
                        use_container_width=True
                    )
                else:
                    st.info("ℹ️ No se encontraron recomendaciones para este cliente")
        
        st.markdown("---")
        
        # Mostrar Top Reglas Generales
        st.markdown("### 🏆 Top 10 Reglas de Asociación (Mayor Lift)")
        top_reglas = df_reglas.nlargest(10, 'Lift')
        
        st.dataframe(
            top_reglas[['Antecedente_Str', 'Consecuente_Str', 'Confianza', 'Lift', 'Soporte']]
            .style.format({
                'Confianza': '{:.2%}',
                'Lift': '{:.2f}',
                'Soporte': '{:.3f}'
            }),
            use_container_width=True
        )
        
    else:
        st.warning("⚠️ Los datos de reglas de asociación no están disponibles. Ejecuta el pipeline ETL completo.")

# ============================================================
# TAB 5: GENERACIÓN DE REPORTES
# ============================================================

with tab5:
    st.markdown('<div class="section-header">📄 Generación de Reportes</div>', unsafe_allow_html=True)
    
    st.markdown("""
    ### 📊 Reporte Ejecutivo Automático
    
    Este módulo genera un informe técnico en formato PDF que incluye:
    - **Descripción de los datos** (dimensiones, variables, calidad)
    - **Metodología de análisis** (ETL, algoritmos ML)
    - **Principales hallazgos visuales** (gráficos exportados)
    - **Resultados de segmentación** (perfiles de clusters)
    - **Resultados de recomendación** (reglas de asociación)
    - **Conclusiones y aplicaciones empresariales**
    """)
    
    st.markdown("---")
    
    # Información del dataset
    st.markdown("### 📋 Información del Dataset")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Dimensiones")
        st.write(f"- **Registros totales:** {len(df_ventas):,}")
        st.write(f"- **Transacciones únicas:** {df_ventas['ID_Transaccion'].nunique():,}")
        st.write(f"- **Productos únicos:** {df_ventas['ID_Producto'].nunique():,}")
        st.write(f"- **Categorías:** {df_ventas['Nombre_Categoria'].nunique():,}")
        st.write(f"- **Tiendas:** {df_ventas['ID_Tienda'].nunique():,}")
    
    with col2:
        st.markdown("#### Rango Temporal")
        st.write(f"- **Fecha inicio:** {df_ventas['Fecha'].min().strftime('%Y-%m-%d')}")
        st.write(f"- **Fecha fin:** {df_ventas['Fecha'].max().strftime('%Y-%m-%d')}")
        st.write(f"- **Días de datos:** {(df_ventas['Fecha'].max() - df_ventas['Fecha'].min()).days}")
    
    st.markdown("---")
    
    # Botón de generación de PDF
    st.markdown("### 📥 Descargar Reporte")
    
    if st.button("🚀 Generar Reporte PDF", type="primary"):
        with st.spinner("Generando reporte..."):
            try:
                from report_generator import generate_pdf_report
                
                pdf_path = generate_pdf_report(
                    df_ventas=df_ventas,
                    df_clusters=df_clusters,
                    df_reglas=df_reglas,
                    df_itemsets=df_itemsets
                )
                
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Descargar Reporte PDF",
                        data=pdf_file,
                        file_name=f"reporte_supermercado_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )
                
                st.success("✅ Reporte generado exitosamente!")
                
            except ImportError:
                st.error("❌ Módulo de generación de PDF no disponible. Instala: `pip install reportlab`")
            except Exception as e:
                st.error(f"❌ Error generando PDF: {e}")

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p><strong>Dashboard de Análisis de Supermercado</strong></p>
    <p>Proyecto Final - Ingeniería de Datos | 2025</p>
    <p>Pipeline ETL: Apache Airflow + PySpark | Dashboard: Streamlit</p>
</div>
""", unsafe_allow_html=True)
