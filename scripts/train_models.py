"""
Script PySpark para Análisis Avanzado: K-Means y FP-Growth
Paso 2.3 del Pipeline ETL

Este script realiza:
1. Segmentación de Clientes usando K-Means (RFM Analysis)
2. Market Basket Analysis usando FP-Growth (Reglas de Asociación)
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, countDistinct, sum as _sum, max as _max, 
    datediff, current_date, collect_list, collect_set, concat_ws, lit, size
)
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml.fpm import FPGrowth
from datetime import datetime
import os



def analyze_customers(spark, df_master):
    """
    Segmentación de clientes usando K-Means
    Métricas RFM: Recencia, Frecuencia, Valor Monetario (simulado por cantidad)
    """
    print("=== INICIANDO SEGMENTACIÓN DE CLIENTES (K-MEANS) ===")
    
    
    df_clientes = df_master.groupBy("ID_Transaccion", "ID_Tienda").agg(
        datediff(current_date(), _max(col("Fecha"))).alias("Recencia_Dias"),
        count("*").alias("Productos_Comprados") 
    )
    
    print(f"Total de clientes únicos: {df_clientes.count()}")
    df_clientes.show(10, truncate=False)
    
    # Preparar features para clustering
    assembler = VectorAssembler(
        inputCols=["Recencia_Dias", "Productos_Comprados"],
        outputCol="features_raw"
    )
    df_features = assembler.transform(df_clientes)
    
    # Normalizar features (StandardScaler)
    scaler = StandardScaler(
        inputCol="features_raw",
        outputCol="features",
        withStd=True,
        withMean=True
    )
    scaler_model = scaler.fit(df_features)
    df_scaled = scaler_model.transform(df_features)
    
    # Encontrar número óptimo de clusters (método del codo - simplified)
    print("\n--- Evaluando número óptimo de clusters ---")
    k_values = range(2, 7)  # Probar de 2 a 6 clusters
    inertias = []
    
    for k in k_values:
        kmeans = KMeans(k=k, seed=42, maxIter=20)
        model = kmeans.fit(df_scaled)
        cost = model.summary.trainingCost
        inertias.append((k, cost))
        print(f"K={k} -> Costo (Inercia): {cost:.2f}")
    
    # Seleccionar K óptimo (puedes ajustar manualmente según el método del codo)
    k_optimo = 4  
    
    # Entrenar modelo final con K óptimo
    print(f"\n--- Entrenando modelo K-Means con K={k_optimo} ---")
    kmeans_final = KMeans(k=k_optimo, seed=42, maxIter=20)
    model_final = kmeans_final.fit(df_scaled)
    
    # Predecir clusters
    df_clustered = model_final.transform(df_scaled)
    df_result = df_clustered.select(
        "ID_Transaccion",
        "ID_Tienda",
        "Recencia_Dias",
        "Productos_Comprados",
        col("prediction").alias("Cluster")
    )
    
    # Mostrar estadísticas por cluster
    print("\n--- Perfil de Clusters ---")
    cluster_stats = df_result.groupBy("Cluster").agg(
        count("*").alias("Num_Clientes"),
        _sum("Recencia_Dias").cast("double").alias("Avg_Recencia"),
        _sum("Productos_Comprados").cast("double").alias("Avg_Productos")
    )
    cluster_stats.orderBy("Cluster").show()
    
    return df_result


def market_basket_analysis(spark, df_master):
    """
    Market Basket Analysis usando FP-Growth
    Encuentra productos frecuentemente comprados juntos
    """
    print("\n=== INICIANDO MARKET BASKET ANALYSIS (FP-GROWTH) ===")
    
    # OPTIMIZACIÓN AGRESIVA: Reducir drásticamente el volumen de datos
    # Tomar solo 10% de las transacciones para evitar OOM
    df_master_sample = df_master.sample(fraction=0.10, seed=42)
    
    # Preparar transacciones: agrupar productos por transacción
    df_transactions = df_master_sample.groupBy("ID_Transaccion").agg(
        collect_set("ID_Producto").alias("items") 
    )
    
    # Filtrar transacciones con al menos 2 productos (canastas válidas)
    # Usar size() para contar elementos en el array
    df_transactions = df_transactions.filter(
        (col("items").isNotNull()) & (size(col("items")) > 1)
    )
    
    # Limitar a máximo 5000 transacciones para análisis
    df_transactions = df_transactions.limit(5000)
    
    total_transactions = df_transactions.count()
    print(f"Total de transacciones (10% sample, max 5000): {total_transactions}")
    
    if total_transactions < 10:
        print("⚠ Transacciones insuficientes para Market Basket Analysis")
        from pyspark.sql.types import StructType, StructField, StringType, DoubleType, ArrayType, IntegerType
        
        # Crear DataFrames vacíos con schema correcto
        itemsets_schema = StructType([
            StructField("items", ArrayType(StringType()), True),
            StructField("freq", IntegerType(), True)
        ])
        rules_schema = StructType([
            StructField("Antecedente_Str", StringType(), True),
            StructField("Consecuente_Str", StringType(), True),
            StructField("Confianza", DoubleType(), True),
            StructField("Lift", DoubleType(), True),
            StructField("Soporte", DoubleType(), True)
        ])
        return spark.createDataFrame([], itemsets_schema), spark.createDataFrame([], rules_schema)
    
    # Aplicar FP-Growth con parámetros MUY conservadores
    print("\n--- Aplicando FP-Growth ---")
    fpGrowth = FPGrowth(
        itemsCol="items",
        minSupport=0.10,  # Soporte mínimo 10% (muy alto para reducir combinaciones)
        minConfidence=0.5,  # Confianza mínima 50%
        numPartitions=4  # Menos particiones para simplificar
    )
    
    model = fpGrowth.fit(df_transactions)
    
    # Conjuntos frecuentes
    frequent_itemsets = model.freqItemsets
    
    # Limitar a top 100 itemsets para evitar operaciones costosas
    frequent_itemsets = frequent_itemsets.orderBy(col("freq").desc()).limit(100)
    
    # Cache DESPUÉS de limitar
    frequent_itemsets.cache()
    
    # Contar (ahora es seguro porque está limitado a 100)
    itemsets_count = frequent_itemsets.count()
    print(f"\nConjuntos frecuentes encontrados (top 100): {itemsets_count}")
    
    if itemsets_count > 0:
        print("\nTop 20 conjuntos frecuentes:")
        frequent_itemsets.show(20, truncate=False)
    else:
        print("⚠ No se encontraron conjuntos frecuentes con el soporte especificado")
    
    # Reglas de asociación
    association_rules = model.associationRules
    
    # Limitar a top 50 reglas para evitar operaciones costosas
    association_rules_limited = association_rules.orderBy(col("lift").desc()).limit(50)
    association_rules_limited.cache()
    
    rules_count = association_rules_limited.count()
    print(f"\nReglas de asociación generadas (top 50): {rules_count}")
    
    if rules_count > 0:
        # Agregar columnas legibles para las reglas
        rules_formatted = association_rules_limited.withColumn(
            "Antecedente_Str", concat_ws(", ", col("antecedent"))
        ).withColumn(
            "Consecuente_Str", concat_ws(", ", col("consequent"))
        ).select(
            "Antecedente_Str",
            "Consecuente_Str",
            col("confidence").alias("Confianza"),
            col("lift").alias("Lift"),
            col("support").alias("Soporte")
        )
        
        print("\nTop 30 reglas de asociación (ordenadas por Lift):")
        rules_formatted.show(30, truncate=False)
    else:
        print("⚠ No se generaron reglas de asociación con los parámetros actuales")
        # Crear DataFrame vacío con el schema correcto
        from pyspark.sql.types import StructType, StructField, StringType, DoubleType
        schema = StructType([
            StructField("Antecedente_Str", StringType(), True),
            StructField("Consecuente_Str", StringType(), True),
            StructField("Confianza", DoubleType(), True),
            StructField("Lift", DoubleType(), True),
            StructField("Soporte", DoubleType(), True)
        ])
        rules_formatted = spark.createDataFrame([], schema)
    
    return frequent_itemsets, rules_formatted


def clean_hdfs_path(spark, path):
    from pyspark import SparkContext
    
    sc = spark.sparkContext
    hadoop_conf = sc._jsc.hadoopConfiguration()
    fs = sc._jvm.org.apache.hadoop.fs.FileSystem.get(hadoop_conf)
    hadoop_path = sc._jvm.org.apache.hadoop.fs.Path(path)
    
    if fs.exists(hadoop_path):
        print(f"  Eliminando directorio existente: {path}")
        fs.delete(hadoop_path, True) 
        return True
    return False


def save_results(df_clusters, df_itemsets, df_rules, output_path, spark):
    """
    Guardar resultados en formato Parquet con configuraciones optimizadas para evitar errores de rename
    """
    print("\n=== GUARDANDO RESULTADOS ===")
    
    # SOLUCIÓN SIMPLE: Usar FileOutputCommitter v2 (compatible con TODAS las versiones)
    # V2 escribe directamente al destino final sin usar rename()
    spark.conf.set("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")
    spark.conf.set("spark.hadoop.mapreduce.fileoutputcommitter.cleanup-failures.ignored", "true")
    spark.conf.set("parquet.enable.summary-metadata", "false")
    
    print("✓ FileOutputCommitter v2 configurado (escribe directo sin rename)")
    
    import os
    import glob
    
    for pattern in ["customer_clusters_*", "frequent_itemsets_*", "association_rules_*"]:
        full_pattern = f"{output_path}/{pattern}"
        # Usar glob para encontrar todos los directorios que coincidan
        for old_dir in glob.glob(full_pattern):
            clean_hdfs_path(spark, old_dir)
            print(f"  Limpiado directorio anterior: {old_dir}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Guardar clusters - Forzar v2 en cada write con options
    clusters_path = f"{output_path}/customer_clusters_{timestamp}"
    print(f"Guardando clusters en {clusters_path}...")
    df_clusters.write \
        .mode("overwrite") \
        .option("mapreduce.fileoutputcommitter.algorithm.version", "2") \
        .option("mapreduce.fileoutputcommitter.marksuccessfuljobs", "false") \
        .option("parquet.enable.summary-metadata", "false") \
        .parquet(clusters_path)
    print(f"✓ Clusters guardados exitosamente")
    
    # Guardar conjuntos frecuentes
    itemsets_path = f"{output_path}/frequent_itemsets_{timestamp}"
    print(f"Guardando itemsets en {itemsets_path}...")
    df_itemsets.write \
        .mode("overwrite") \
        .option("mapreduce.fileoutputcommitter.algorithm.version", "2") \
        .option("mapreduce.fileoutputcommitter.marksuccessfuljobs", "false") \
        .option("parquet.enable.summary-metadata", "false") \
        .parquet(itemsets_path)
    print(f"✓ Itemsets guardados exitosamente")
    
    # Guardar reglas de asociación
    rules_path = f"{output_path}/association_rules_{timestamp}"
    print(f"Guardando reglas en {rules_path}...")
    df_rules.write \
        .mode("overwrite") \
        .option("mapreduce.fileoutputcommitter.algorithm.version", "2") \
        .option("mapreduce.fileoutputcommitter.marksuccessfuljobs", "false") \
        .option("parquet.enable.summary-metadata", "false") \
        .parquet(rules_path)
    print(f"✓ Reglas guardadas exitosamente")
    
    # Crear symlinks a "latest" dentro del mismo directorio analytics
    # para que export_to_csv.py pueda encontrarlos
    
    # Symlink para clusters (dentro de /opt/spark/data/analytics/)
    latest_clusters = f"{output_path}/customer_clusters_latest"
    if os.path.exists(latest_clusters):
        os.remove(latest_clusters)
    os.symlink(clusters_path, latest_clusters)
    print(f"Symlink creado: {latest_clusters} -> {clusters_path}")
    
    # Symlink para itemsets
    latest_itemsets = f"{output_path}/frequent_itemsets_latest"
    if os.path.exists(latest_itemsets):
        os.remove(latest_itemsets)
    os.symlink(itemsets_path, latest_itemsets)
    print(f"Symlink creado: {latest_itemsets} -> {itemsets_path}")
    
    # Symlink para rules
    latest_rules = f"{output_path}/association_rules_latest"
    if os.path.exists(latest_rules):
        os.remove(latest_rules)
    os.symlink(rules_path, latest_rules)
    print(f"Symlink creado: {latest_rules} -> {rules_path}")
    
    # Limpiar directorios _temporary residuales
    # Nota: Los warnings "Failed to delete" son esperados con FileOutputCommitter v2
    # porque Spark intenta borrar archivos que ya están siendo movidos.
    # Esto es NORMAL y no afecta la integridad de los datos.
    print("\n=== LIMPIANDO DIRECTORIOS TEMPORALES ===")
    import shutil
    import time
    try:
        # Dar 1 segundo para que Spark termine todas las operaciones internas
        time.sleep(1)
        
        for dir_pattern in [clusters_path, itemsets_path, rules_path]:
            temp_dir = f"{dir_pattern}/_temporary"
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                print(f"✓ Limpiado: {temp_dir}")
    except Exception as e:
        print(f"⚠ Error limpiando temporales (no crítico): {e}")
    
    print("\n=== RESUMEN DE ARCHIVOS GUARDADOS ===")
    print(f"✓ Clusters: {clusters_path}")
    print(f"✓ Itemsets: {itemsets_path}")
    print(f"✓ Reglas: {rules_path}")
    print("="*60)


def main():
    """
    Función principal
    """
    print("="*60)
    print("ANÁLISIS AVANZADO - K-MEANS & FP-GROWTH")
    print("="*60)
    
    # Crear SparkSession
    spark = SparkSession.builder \
        .appName("Supermarket_Advanced_Analytics") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()
    
    # Rutas
    input_path = "/opt/spark/data/processed/transactions_master_latest"
    output_path = "/opt/spark/data/analytics"
    
    print(f"\nLeyendo datos procesados desde: {input_path}")
    
    # Leer datos procesados del paso anterior
    df_master = spark.read.parquet(input_path)
    
    print(f"Total de registros: {df_master.count()}")
    print("Schema:")
    df_master.printSchema()
    
    # 1. Segmentación de Clientes (K-Means)
    df_clusters = analyze_customers(spark, df_master)
    
    # 2. Market Basket Analysis (FP-Growth)
    df_itemsets, df_rules = market_basket_analysis(spark, df_master)
    
    # 3. Guardar resultados
    save_results(df_clusters, df_itemsets, df_rules, output_path, spark)
    
    print("\n" + "="*60)
    print("✓ ANÁLISIS COMPLETADO EXITOSAMENTE")
    print("="*60)
    
    spark.stop()


if __name__ == "__main__":
    main()
