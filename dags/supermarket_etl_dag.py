from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.sensors.filesystem import FileSensor
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# Definición de argumentos por defecto
default_args = {
    'owner': 'ingeniero_datos',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Definición del DAG
with DAG(
    'supermarket_etl_pipeline',
    default_args=default_args,
    description='ETL de Transacciones de Supermercado usando Spark',
    schedule_interval=None, # Ejecución manual para el taller
    start_date=datetime(2023, 1, 1),
    catchup=False,
    tags=['taller', 'spark', 'etl'],
) as dag:

    # Paso 2.1: Sensor de Extracción (Simulación)
    # Verifica que existan archivos en la carpeta raw antes de empezar
    check_files_sensor = FileSensor(
        task_id='wait_for_transactions_files',
        filepath='/opt/spark/data/raw/Transactions',
        fs_conn_id='fs_default', 
        poke_interval=30, 
        timeout=600 
    )

    # Paso 2.2: Transformación con PySpark
    # Envía el trabajo al contenedor de Spark Master
    transform_data = SparkSubmitOperator(
        task_id='spark_transform_job',
        application='/opt/spark/scripts/transform_data.py',
        conn_id='spark_default',
        verbose=True,
        # Configuración de recursos para Spark
        conf={
            "spark.master": "spark://spark-master:7077"
        }
    )
    
    # Paso 2.3: Análisis Avanzado (K-Means + FP-Growth)
    # Ejecuta segmentación de clientes y market basket analysis
    advanced_analytics = SparkSubmitOperator(
        task_id='spark_advanced_analytics',
        application='/opt/spark/scripts/train_models.py',
        conn_id='spark_default',
        verbose=True,
        conf={
            "spark.master": "spark://spark-master:7077"
        }
    )
    
    # Paso 2.4: Exportación a CSV
    # Convierte Parquet a CSV para consumo del Dashboard
    export_csv = SparkSubmitOperator(
        task_id='export_final_csv',
        application='/opt/spark/scripts/export_to_csv.py',
        conn_id='spark_default',
        verbose=True,
        conf={
            "spark.master": "spark://spark-master:7077"
        }
    )
    
    end_task = BashOperator(
        task_id='etl_completed',
        bash_command='echo "✓ Pipeline ETL completado: Extracción → Transformación → ML Analytics → Export CSV"'
    )

    # Definición del flujo completo (Pipeline lineal)
    # 2.1 → 2.2 → 2.3 → 2.4 → Fin
    check_files_sensor >> transform_data >> advanced_analytics >> export_csv >> end_task