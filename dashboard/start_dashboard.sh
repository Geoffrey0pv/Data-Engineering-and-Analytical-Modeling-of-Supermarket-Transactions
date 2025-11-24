#!/bin/bash
# Script de inicio rápido para el Dashboard
# Ejecutar: bash start_dashboard.sh

echo "============================================================"
echo "🚀 INICIANDO DASHBOARD - ANÁLISIS DE SUPERMERCADO"
echo "============================================================"
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar que los datos existen
echo "🔍 Verificando datos procesados..."

if docker exec proyectofinal-spark-master-1 ls /opt/spark/data/output/ventas_detalladas.csv/part-*.csv > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Datos encontrados${NC}"
else
    echo -e "${RED}❌ ERROR: Datos no encontrados${NC}"
    echo ""
    echo "Los archivos CSV no están disponibles en /opt/spark/data/output/"
    echo "Por favor, ejecuta el pipeline ETL primero:"
    echo ""
    echo "  1. Ir a Airflow UI: http://localhost:8080"
    echo "  2. Ejecutar DAG: supermarket_etl_pipeline"
    echo "  3. Esperar a que complete todos los tasks"
    echo ""
    exit 1
fi

echo ""
echo "📦 Instalando dependencias de Python..."

cd "/home/docker/prueba/Proyecto Final/dashboard"

# Verificar si requirements está instalado
if python3 -c "import streamlit" 2>/dev/null; then
    echo -e "${GREEN}✅ Dependencias ya instaladas${NC}"
else
    echo "Instalando paquetes..."
    pip install -q -r requirements.txt
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Dependencias instaladas${NC}"
    else
        echo -e "${RED}❌ Error instalando dependencias${NC}"
        exit 1
    fi
fi

echo ""
echo "🚀 Iniciando Streamlit Dashboard..."
echo ""
echo "============================================================"
echo -e "${GREEN}✅ Dashboard disponible en:${NC}"
echo ""
echo "   🌐 URL: http://localhost:8501"
echo ""
echo "============================================================"
echo ""
echo "💡 Funcionalidades disponibles:"
echo "   • Resumen Ejecutivo (KPIs, Top Rankings)"
echo "   • Análisis Temporal (Serie tiempo, Heatmap, Boxplot)"
echo "   • Segmentación K-Means (4 clusters con recomendaciones)"
echo "   • Recomendador FP-Growth (Por producto o cliente)"
echo "   • Generación de Reportes PDF"
echo ""
echo "🛑 Para detener: Presiona Ctrl+C"
echo ""
echo "============================================================"
echo ""

# Ejecutar Streamlit
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
