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
        filepath='/opt/airflow/data/raw/Transactions', # Ruta dentro del container de Airflow
        fs_conn_id='fs_default', # Conexión por defecto al sistema de archivos local
        poke_interval=30, # Revisa cada 30 segundos
        timeout=600 # Falla si no encuentra archivos en 10 mins
    )

    # Paso 2.2: Transformación con PySpark
    # Envía el trabajo al contenedor de Spark Master
    transform_data = SparkSubmitOperator(
        task_id='spark_transform_job',
        application='/opt/airflow/scripts/transform_data.py', # Ruta del script visto desde Airflow
        conn_id='spark_default', # Necesitaremos configurar esto en la UI
        verbose=True,
        # Configuración de recursos para Spark
        conf={
            "spark.master": "spark://spark-master:7077"
        }
    )
    
    end_task = BashOperator(
        task_id='etl_completed',
        bash_command='echo "ETL de la Fase 2 finalizado correctamente."'
    )

    # Definición del flujo
    check_files_sensor >> transform_data >> end_task