"""
Script PySpark para Exportar Resultados a CSV
Paso 2.4 del Pipeline ETL

Este script toma los Parquet generados y los convierte a CSV
para consumo del Dashboard y reportes.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, concat_ws
import os
import shutil
import glob

def export_to_csv(spark, input_path, output_path, name):
    """
    Lee un Parquet y lo exporta a CSV con nombre limpio
    """
    print(f"\n--- Exportando {name} ---")
    
    # Leer Parquet
    df = spark.read.parquet(input_path)
    record_count = df.count()
    print(f"Registros a exportar: {record_count}")
    
    if record_count == 0:
        print(f"⚠ ADVERTENCIA: {name} tiene 0 registros")
        return None
    
    # Usar directorio temporal primero
    temp_csv_dir = f"{output_path}/_temp_{name}"
    
    # Limpiar directorio temporal si existe
    import shutil
    if os.path.exists(temp_csv_dir):
        shutil.rmtree(temp_csv_dir)
    
    # Exportar a CSV en directorio temporal con coalesce(1) para un solo archivo
    print(f"Escribiendo a directorio temporal: {temp_csv_dir}")
    df.coalesce(1).write \
        .mode("overwrite") \
        .option("header", "true") \
        .option("encoding", "UTF-8") \
        .csv(temp_csv_dir)
    
    # Buscar el archivo part-*.csv generado
    import glob
    csv_files = glob.glob(f"{temp_csv_dir}/part-*.csv")
    
    if not csv_files:
        print(f"⚠ ERROR: No se generó archivo CSV en {temp_csv_dir}")
        return None
    
    # Mover el archivo a la ubicación final con nombre limpio
    final_csv_path = f"{output_path}/{name}.csv"
    source_file = csv_files[0]
    
    print(f"Moviendo {source_file} -> {final_csv_path}")
    shutil.move(source_file, final_csv_path)
    
    # Limpiar directorio temporal
    shutil.rmtree(temp_csv_dir)
    
    print(f"✓ Exportado exitosamente: {final_csv_path}")
    
    return final_csv_path


def export_transactions_master(spark, transactions_path, output_path):
    """
    Exporta las transacciones maestras procesadas
    Incluye todas las columnas relevantes para el dashboard
    """
    print("\n=== EXPORTANDO TRANSACCIONES MAESTRAS ===")
    
    df = spark.read.parquet(transactions_path)
    
    # Seleccionar columnas relevantes (solo las que existen en el DataFrame)
    df_export = df.select(
        "ID_Transaccion",
        "ID_Tienda",
        "ID_Producto",
        "ID_Categoria",
        "Nombre_Categoria",
        "Fecha",
        "Hora",
        "Año",
        "Mes",
        "Dia",
        "Dia_Semana",
        "Semana_Año",
        "HoraDelDia",
        "DiaSemana"
    )
    
    csv_path = export_to_csv(spark, transactions_path, output_path, "ventas_detalladas")
    
    return csv_path


def export_customer_clusters(spark, clusters_path, output_path):
    """
    Exporta los clusters de clientes
    """
    print("\n=== EXPORTANDO CLUSTERS DE CLIENTES ===")
    
    df = spark.read.parquet(clusters_path)
    
    csv_path = export_to_csv(spark, clusters_path, output_path, "clientes_clusters")
    
    return csv_path


def export_association_rules(spark, rules_path, output_path):
    """
    Exporta las reglas de asociación
    """
    print("\n=== EXPORTANDO REGLAS DE ASOCIACIÓN ===")
    
    df = spark.read.parquet(rules_path)
    
    # Ordenar por Lift descendente (las mejores recomendaciones primero)
    df_sorted = df.orderBy(col("Lift").desc())
    
    csv_path = export_to_csv(spark, rules_path, output_path, "reglas_asociacion")
    
    return csv_path


def export_frequent_itemsets(spark, itemsets_path, output_path):
    """
    Exporta los conjuntos frecuentes
    """
    print("\n=== EXPORTANDO CONJUNTOS FRECUENTES ===")
    
    df = spark.read.parquet(itemsets_path)
    
    # Convertir array de items a string para CSV
    df_formatted = df.withColumn(
        "items_str", concat_ws(", ", col("items"))
    ).select(
        col("items_str").alias("Productos"),
        col("freq").alias("Frecuencia")
    ).orderBy(col("Frecuencia").desc())
    
    record_count = df_formatted.count()
    print(f"Registros a exportar: {record_count}")
    
    if record_count == 0:
        print(f"⚠ ADVERTENCIA: conjuntos_frecuentes tiene 0 registros")
        return None
    
    # Usar directorio temporal
    import shutil
    temp_csv_dir = f"{output_path}/_temp_conjuntos_frecuentes"
    
    if os.path.exists(temp_csv_dir):
        shutil.rmtree(temp_csv_dir)
    
    # Exportar
    print(f"Escribiendo a directorio temporal: {temp_csv_dir}")
    df_formatted.coalesce(1).write \
        .mode("overwrite") \
        .option("header", "true") \
        .option("encoding", "UTF-8") \
        .csv(temp_csv_dir)
    
    # Buscar archivo generado
    import glob
    csv_files = glob.glob(f"{temp_csv_dir}/part-*.csv")
    
    if not csv_files:
        print(f"⚠ ERROR: No se generó archivo CSV")
        return None
    
    # Mover a ubicación final
    final_csv_path = f"{output_path}/conjuntos_frecuentes.csv"
    source_file = csv_files[0]
    
    print(f"Moviendo {source_file} -> {final_csv_path}")
    shutil.move(source_file, final_csv_path)
    
    # Limpiar temporal
    shutil.rmtree(temp_csv_dir)
    
    print(f"✓ Exportado exitosamente: {final_csv_path}")
    
    return final_csv_path


def main():
    """
    Función principal
    """
    print("="*60)
    print("EXPORTACIÓN A CSV PARA DASHBOARD")
    print("="*60)
    
    # Crear SparkSession con FileOutputCommitter v2 para CSV
    spark = SparkSession.builder \
        .appName("Supermarket_Export_CSV") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2") \
        .config("spark.hadoop.mapreduce.fileoutputcommitter.cleanup-failures.ignored", "true") \
        .getOrCreate()
    
    print("✓ FileOutputCommitter v2 configurado para CSV (sin rename)")
    
    # Rutas de entrada (symlinks a los últimos datos generados)
    transactions_path = "/opt/spark/data/processed/transactions_master_latest"
    clusters_path = "/opt/spark/data/analytics/customer_clusters_latest"
    itemsets_path = "/opt/spark/data/analytics/frequent_itemsets_latest"
    rules_path = "/opt/spark/data/analytics/association_rules_latest"
    
    # Ruta de salida
    output_path = "/opt/spark/data/output"
    
    # Crear directorio de salida si no existe
    os.makedirs(output_path, exist_ok=True)
    
    print(f"\nDirectorio de salida: {output_path}")
    
    # Exportar cada dataset
    try:
        export_transactions_master(spark, transactions_path, output_path)
    except Exception as e:
        print(f"⚠ Error exportando transacciones: {e}")
    
    try:
        export_customer_clusters(spark, clusters_path, output_path)
    except Exception as e:
        print(f"⚠ Error exportando clusters: {e}")
    
    try:
        export_association_rules(spark, rules_path, output_path)
    except Exception as e:
        print(f"⚠ Error exportando reglas: {e}")
    
    try:
        export_frequent_itemsets(spark, itemsets_path, output_path)
    except Exception as e:
        print(f"⚠ Error exportando conjuntos frecuentes: {e}")
    
    print("\n" + "="*60)
    print("✓ EXPORTACIÓN COMPLETADA")
    print(f"   Archivos CSV disponibles en: {output_path}")
    print("="*60)
    
    spark.stop()


if __name__ == "__main__":
    main()
