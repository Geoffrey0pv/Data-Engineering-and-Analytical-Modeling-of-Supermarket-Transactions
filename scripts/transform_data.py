from pyspark.sql import SparkSession
from pyspark.sql.functions import col, split, explode, to_date, year, month, dayofweek, hour, weekofyear, date_format
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DateType
import shutil
import os

def process_data():
    # 1. Inicializar Spark Session
    spark = SparkSession.builder \
        .appName("Supermarket_ETL_Transformation") \
        .getOrCreate()

    base_path = "/opt/spark/data/raw"

    # Esquema para Categories (ID|Nombre)
    cat_schema = StructType([
        StructField("ID_Categoria", IntegerType(), True),
        StructField("Nombre_Categoria", StringType(), True)
    ])
    
    df_categories = spark.read.csv(
        f"{base_path}/Products/Categories.csv", 
        sep='|', 
        header=False, 
        schema=cat_schema
    )

    # Esquema para ProductCategory (Producto|Categoria)
    df_prod_cat = spark.read.csv(
        f"{base_path}/Products/ProductCategory.csv", 
        sep='|', 
        header=True,
        inferSchema=True
    ).withColumnRenamed("v.Code_pr", "ID_Producto") \
     .withColumnRenamed("v.code", "ID_Categoria")

    # --- LECTURA Y UNIFICACIÓN DE TRANSACCIONES ---
    
    # Esquema común para transacciones
    # Fecha|ID_Tienda|ID_Transaccion|ID_Productos(String "1 2 3")
    tran_schema = StructType([
        StructField("Fecha", StringType(), True),
        StructField("ID_Tienda", IntegerType(), True),
        StructField("ID_Transaccion", IntegerType(), True),
        StructField("ID_Productos_Raw", StringType(), True)
    ])

    # Leemos los archivos de transacciones. 
    df_trans = spark.read.csv(
        f"{base_path}/Transactions/*_Tran.csv", 
        sep='|', 
        header=False,
        schema=tran_schema
    )

    # Filtrar filas que sean headers (si algún archivo tenía header 'Fecha|...')
    df_trans = df_trans.filter(col("ID_Tienda").isNotNull())

    # --- TRANSFORMACIÓN (El "Core" de la lógica) ---

    # 1. Explode: Convertir "20 3 1" en filas separadas
    # Split por espacio " " y luego Explode
    df_exploded = df_trans.withColumn(
        "ID_Producto", 
        explode(split(col("ID_Productos_Raw"), " "))
    ).drop("ID_Productos_Raw")

    # 2. Casteo de Tipos
    df_exploded = df_exploded \
        .withColumn("ID_Producto", col("ID_Producto").cast(IntegerType())) \
        .withColumn("Fecha", to_date(col("Fecha"), "yyyy-MM-dd"))

    # Limpiar nulos generados por el explode (espacios vacíos)
    df_exploded = df_exploded.filter(col("ID_Producto").isNotNull())

    # --- ENRIQUECIMIENTO (Joins) ---
    
    # Unir con Categorías y Nombres
    # Transacciones -> ProdCat -> Categories
    df_enriched = df_exploded.join(df_prod_cat, on="ID_Producto", how="left") \
                             .join(df_categories, on="ID_Categoria", how="left")

    # --- INGENIERÍA DE CARACTERÍSTICAS (Tiempo) ---
    
    df_final = df_enriched \
        .withColumn("Año", year(col("Fecha"))) \
        .withColumn("Mes", month(col("Fecha"))) \
        .withColumn("Dia", date_format(col("Fecha"), "d")) \
        .withColumn("Dia_Semana", dayofweek(col("Fecha"))) \
        .withColumn("Semana_Año", weekofyear(col("Fecha"))) \
        .withColumn("Nombre_Categoria", 
                    col("Nombre_Categoria")) 
    
    
    df_final = df_final.fillna({"Nombre_Categoria": "DESCONOCIDA"})
    
    # Usar timestamp para generar un directorio único y evitar conflictos de permisos
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"/opt/spark/data/processed/transactions_master_{timestamp}"
    
    print(f"Escribiendo datos procesados en: {output_path}")
    
    df_final.write.mode("overwrite").parquet(output_path)
    
    # Crear un symlink al directorio más reciente
    import subprocess
    latest_link = "/opt/spark/data/processed/transactions_master_latest"
    try:
        if os.path.exists(latest_link) or os.path.islink(latest_link):
            os.unlink(latest_link)
        os.symlink(output_path, latest_link)
        print(f"Symlink creado: {latest_link} -> {output_path}")
    except Exception as e:
        print(f"No se pudo crear symlink: {e}")

    print("Transformación completada exitosamente.")
    spark.stop()

if __name__ == "__main__":
    process_data()