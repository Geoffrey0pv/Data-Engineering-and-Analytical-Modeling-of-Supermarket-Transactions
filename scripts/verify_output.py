"""
Script de verificación para inspeccionar los archivos generados por el pipeline
"""
from pyspark.sql import SparkSession

def main():
    spark = SparkSession.builder \
        .appName("Verify_Pipeline_Output") \
        .getOrCreate()
    
    print("="*70)
    print("VERIFICACIÓN DE ARCHIVOS GENERADOS POR EL PIPELINE")
    print("="*70)
    
    # 1. Verificar transacciones maestras
    print("\n1. TRANSACCIONES MAESTRAS (Paso 2.2)")
    print("-" * 70)
    try:
        df_transactions = spark.read.parquet("/opt/spark/data/processed/transactions_master_latest")
        print(f"✓ Total registros: {df_transactions.count():,}")
        print("✓ Schema:")
        df_transactions.printSchema()
        print("\n✓ Muestra de datos:")
        df_transactions.show(5, truncate=False)
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 2. Verificar clusters
    print("\n2. CLUSTERS DE CLIENTES (Paso 2.3 - K-Means)")
    print("-" * 70)
    try:
        df_clusters = spark.read.parquet("/opt/spark/data/analytics/customer_clusters_latest")
        print(f"✓ Total clientes segmentados: {df_clusters.count():,}")
        print("\n✓ Distribución por cluster:")
        df_clusters.groupBy("Cluster").count().orderBy("Cluster").show()
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 3. Verificar reglas de asociación
    print("\n3. REGLAS DE ASOCIACIÓN (Paso 2.3 - FP-Growth)")
    print("-" * 70)
    try:
        df_rules = spark.read.parquet("/opt/spark/data/analytics/association_rules_latest")
        print(f"✓ Total reglas generadas: {df_rules.count():,}")
        print("\n✓ Top 10 reglas por Lift:")
        df_rules.orderBy("Lift", ascending=False).show(10, truncate=False)
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # 4. Verificar conjuntos frecuentes
    print("\n4. CONJUNTOS FRECUENTES (Paso 2.3 - FP-Growth)")
    print("-" * 70)
    try:
        df_itemsets = spark.read.parquet("/opt/spark/data/analytics/frequent_itemsets_latest")
        print(f"✓ Total conjuntos frecuentes: {df_itemsets.count():,}")
        print("\n✓ Top 15 más frecuentes:")
        df_itemsets.orderBy("freq", ascending=False).show(15, truncate=False)
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*70)
    print("VERIFICACIÓN COMPLETADA")
    print("="*70)
    
    spark.stop()

if __name__ == "__main__":
    main()
