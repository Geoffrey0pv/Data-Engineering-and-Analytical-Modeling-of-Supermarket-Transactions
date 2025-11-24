# 🏗️ Arquitectura ETL Completa - Sistema de Análisis de Supermercado

## 📋 Índice
1. [Vista General de la Infraestructura](#vista-general)
2. [Componentes Docker](#componentes-docker)
3. [Flujo de Datos Completo](#flujo-de-datos)
4. [Procesamiento Distribuido](#procesamiento-distribuido)
5. [Limitaciones y Por Qué Ocurren](#limitaciones)
6. [Soluciones Industriales](#soluciones-industriales)

---

## 🌐 Vista General de la Infraestructura

```
┌─────────────────────────────────────────────────────────────────┐
│                        ARQUITECTURA ETL                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │   AIRFLOW    │────▶│     SPARK    │────▶│   OUTPUTS    │   │
│  │  Scheduler   │     │   Cluster    │     │  (Parquet/   │   │
│  │  Webserver   │     │  Master+     │     │    CSV)      │   │
│  │              │     │  Workers     │     │              │   │
│  └──────────────┘     └──────────────┘     └──────────────┘   │
│         │                     │                     │           │
│         │                     │                     │           │
│         ▼                     ▼                     ▼           │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              VOLÚMENES COMPARTIDOS (Docker)               │ │
│  │  /data/raw  │  /data/processed  │  /data/analytics      │ │
│  │  /scripts   │  /logs             │  /dags                 │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🐳 Componentes Docker

### **1. Airflow (Orquestador)**

**Contenedor:** `airflow-webserver` + `airflow-scheduler`

```yaml
# docker-compose.yml
airflow-webserver:
  image: apache/airflow:2.x
  ports:
    - "8080:8080"  # UI Web
  volumes:
    - ./dags:/opt/airflow/dags           # DAGs Python
    - ./data:/opt/airflow/data           # Datos compartidos
    - ./scripts:/opt/spark/scripts       # Scripts PySpark
    - ./logs:/opt/airflow/logs           # Logs de ejecución
```

**Responsabilidades:**
- ✅ Programar tareas (scheduling)
- ✅ Monitorear estado del pipeline
- ✅ Reintentar tareas fallidas
- ✅ Gestionar dependencias entre tareas
- ⚠️ **NO procesa datos** (solo orquesta)

**Recursos Asignados:**
```
CPU: Compartido (sin límite)
RAM: Compartido (sin límite)
Almacenamiento: Volúmenes Docker
```

---

### **2. Spark Master (Coordinador)**

**Contenedor:** `spark-master`

```yaml
spark-master:
  image: bitnami/spark:3.5
  ports:
    - "7077:7077"  # Puerto de comunicación con workers
    - "8081:8080"  # UI Web Spark Master
  environment:
    - SPARK_MODE=master
```

**Responsabilidades:**
- ✅ Recibir trabajos de Airflow
- ✅ Dividir tareas en stages
- ✅ Asignar tareas a workers
- ✅ Gestionar shuffle operations
- ⚠️ **NO ejecuta código** (solo coordina)

**Recursos Asignados:**
```
CPU: ~1-2 cores
RAM: ~512 MB - 1 GB
Red: Puerto 7077 (RPC)
```

---

### **3. Spark Workers (Ejecutores)**

**Contenedores:** `spark-worker-1`, `spark-worker-2`, ...

```yaml
spark-worker-1:
  image: bitnami/spark:3.5
  environment:
    - SPARK_MODE=worker
    - SPARK_MASTER_URL=spark://spark-master:7077
    - SPARK_WORKER_MEMORY=1G      # 1 GB de RAM por worker
    - SPARK_WORKER_CORES=2        # 2 CPU cores por worker
```

**Responsabilidades:**
- ✅ **EJECUTAR CÓDIGO PYSPARK** (transformaciones)
- ✅ Leer/escribir datos del filesystem
- ✅ Cachear RDDs en memoria
- ✅ Realizar operaciones shuffle
- ✅ Reportar estado al Master

**Recursos Asignados (por worker):**
```
CPU: 2 cores
RAM: 1 GB
Almacenamiento: /tmp (temporal para shuffle)
```

---

## 🔄 Flujo de Datos Completo (ETL Pipeline)

### **Paso 1: Inicio del DAG (Airflow)**

```python
# dags/supermarket_etl_dag.py
@dag(
    schedule_interval='@daily',  # Ejecuta diariamente
    start_date=datetime(2025, 1, 1),
    catchup=False
)
def supermarket_etl_pipeline():
    # ...
```

**¿Qué pasa aquí?**
1. **Airflow Scheduler** escanea el directorio `/dags` cada 5 segundos
2. Detecta que el DAG debe ejecutarse
3. Crea un **DagRun** (instancia de ejecución)
4. Encola las tareas en la cola de ejecución

**Ubicación física:**
```
Container: airflow-scheduler
Proceso: Python (airflow/jobs/scheduler_job.py)
CPU: Mínimo (~100 MB RAM, 0.1 CPU)
```

---

### **Paso 2: FileSensor (Espera de Datos)**

```python
wait_for_data = FileSensor(
    task_id='wait_for_raw_data',
    filepath='/opt/airflow/data/raw/Transactions/*.csv',
    fs_conn_id='fs_default',
    poke_interval=30  # Revisa cada 30 segundos
)
```

**¿Qué pasa aquí?**
1. Airflow Worker ejecuta un **poller** que revisa si existen archivos
2. Si NO existen → Espera 30s y vuelve a revisar
3. Si existen → Marca la tarea como SUCCESS
4. **NO MUEVE DATOS**, solo verifica existencia

**Ubicación física:**
```
Container: airflow-webserver (executor local)
Filesystem: /opt/airflow/data/raw/Transactions/
Operación: os.path.exists() - sin carga de CPU
```

---

### **Paso 3: Transformación PySpark (spark_transform)**

```python
spark_transform = SparkSubmitOperator(
    task_id='spark_transform',
    application='/opt/spark/scripts/transform_data.py',
    conn_id='spark_default',  # spark://spark-master:7077
    conf={
        'spark.executor.memory': '1g',
        'spark.executor.cores': '2'
    }
)
```

**¿Qué pasa aquí? (Paso a Paso)**

#### **3.1. Airflow envía el job a Spark Master**
```
Airflow Webserver 
    ↓ (HTTP REST API)
Spark Master (puerto 7077)
    ↓ "Necesito ejecutar /opt/spark/scripts/transform_data.py"
```

#### **3.2. Spark Master crea un DAG de ejecución**
```python
# Spark internamente hace:
# 1. Leer CSV → RDD[Row]
df = spark.read.csv("/opt/airflow/data/raw/Transactions/*.csv")

# Esto se convierte en:
# Stage 0: Scan CSV files (narrow transformation)
# └─ Task 0: Read partition 1
# └─ Task 1: Read partition 2
# └─ Task 2: Read partition 3
```

#### **3.3. Spark Master asigna tareas a Workers**
```
Spark Master:
  "Worker-1: Ejecuta Task 0 (partition 1)"
  "Worker-2: Ejecuta Task 1 (partition 2)"

Worker-1 (Container spark-worker-1):
  ├─ Lee /data/raw/Transactions/part-00001.csv
  ├─ Parsea CSV → RDD[Row]
  └─ Mantiene en memoria (cache)
```

#### **3.4. Transformaciones (filtros, joins, agregaciones)**
```python
# Script: transform_data.py
df_transactions.join(df_products, "ID_Producto") \
    .filter(col("Precio") > 0) \
    .groupBy("ID_Tienda") \
    .agg(sum("Precio"))

# Esto genera:
# Stage 1: Join (SHUFFLE) ← Mueve datos entre workers
#   ├─ Worker-1 envía particiones a Worker-2
#   └─ Worker-2 envía particiones a Worker-1
#
# Stage 2: Aggregation (SHUFFLE)
#   └─ Agrupa por ID_Tienda (puede requerir mover datos)
```

**🔴 AQUÍ OCURRE EL CUELLO DE BOTELLA:**
```
Worker-1: "Necesito datos de la partición 5"
    ↓ (Red TCP/IP entre containers)
Worker-2: "Aquí están los 50 MB de datos"
    ↓ (Si Worker-2 se cae o se queda sin RAM...)
Worker-1: "ERROR: Missing shuffle partition 5"
    ↓
Job FAILS (MetadataFetchFailedException)
```

#### **3.5. Escritura de Resultados**
```python
df_master.write \
    .mode("overwrite") \
    .parquet("/opt/airflow/data/processed/transactions_master_latest")

# Spark hace:
# Stage 3: Write to disk
#   ├─ Worker-1 escribe part-00000.parquet
#   ├─ Worker-2 escribe part-00001.parquet
#   └─ Worker-3 escribe part-00002.parquet
```

**Ubicación física:**
```
Containers: spark-worker-1, spark-worker-2
Procesos: JVM (Executor) ejecutando PySpark
CPU: 2 cores × 2 workers = 4 cores total
RAM: 1 GB × 2 workers = 2 GB total
Network: TCP entre workers (shuffle)
Disk I/O: Lectura de CSV + Escritura de Parquet
```

---

### **Paso 4: Análisis Avanzado (FP-Growth)**

```python
spark_advanced_analytics = SparkSubmitOperator(
    task_id='spark_advanced_analytics',
    application='/opt/spark/scripts/train_models.py'
)
```

**¿Qué pasa aquí? (Por Qué Falla)**

#### **4.1. Construcción del FP-Tree**
```python
# train_models.py
df_transactions = df_master.groupBy("ID_Transaccion").agg(
    collect_set("ID_Producto").alias("items")
)

# Spark hace:
# Stage N: Group by transaction → SHUFFLE
#   ├─ Todas las transacciones con mismo ID 
#   │   deben ir al mismo worker
#   └─ Si hay 1M de transacciones únicas...
#       └─ 1M de particiones a redistribuir!
```

**🔴 PROBLEMA 1: Shuffle Masivo**
```
Worker-1 tiene: [Tx1, Tx2, Tx3, Tx5, Tx7, ...]
Worker-2 necesita: [Tx1, Tx3, Tx5] para su partition

Worker-1 envía 500 MB de datos → Worker-2
Worker-2 envía 450 MB de datos → Worker-1
...
Total datos movidos: 2-3 GB entre workers

Si Worker-2 se queda sin RAM mientras recibe:
  → OutOfMemoryError
  → Executor KILLED (exit code 52)
  → Shuffle metadata LOST
  → Job FAILS
```

#### **4.2. Algoritmo FP-Growth**
```python
model = FPGrowth(minSupport=0.10).fit(df_transactions)

# Spark hace internamente:
# Stage N+1: Contar frecuencia de items → SHUFFLE
# Stage N+2: Ordenar por frecuencia → SHUFFLE
# Stage N+3: Construir FP-Tree en memoria → RAM INTENSIVO
#   ├─ Si hay 10,000 productos únicos
#   │   y 100,000 transacciones...
#   └─ FP-Tree puede ocupar 500 MB - 2 GB de RAM
#
# Stage N+4: Minar patrones → SHUFFLE
#   ├─ Para cada nodo del árbol
#   │   genera combinaciones recursivas
#   └─ Millones de combinaciones → SHUFFLE masivo
#
# Stage N+5: Generar reglas → SHUFFLE
```

**🔴 PROBLEMA 2: Memoria Insuficiente**
```
Worker-1 (1 GB RAM):
  ├─ JVM overhead: 200 MB
  ├─ PySpark process: 100 MB
  ├─ Cached RDDs: 300 MB
  ├─ FP-Tree construction: 600 MB
  └─ TOTAL: 1.2 GB > 1 GB limit
      → OutOfMemoryError
      → Job FAILS
```

**Ubicación física:**
```
Containers: spark-worker-1, spark-worker-2
RAM Utilizada: 90-100% (1 GB cada uno)
CPU: 80-100% (procesamiento intensivo)
Network: Saturada (shuffle operations)
Disk: /tmp lleno (spill to disk cuando RAM llena)
```

---

## ⚙️ Procesamiento Distribuido: ¿Cómo Funciona Realmente?

### **Conceptos Clave:**

#### **1. Particionamiento de Datos**
```python
# Cuando lees 1M de registros con 2 workers:
df = spark.read.csv("data.csv")  # 1M rows

# Spark divide automáticamente:
Worker-1: Partitions [0-99]    → 500K rows
Worker-2: Partitions [100-199] → 500K rows

# Cada worker procesa SU partición independientemente
```

#### **2. Transformaciones Narrow vs Wide**

**Narrow (sin shuffle - RÁPIDO):**
```python
df.filter(col("price") > 10)   # Cada worker filtra su data
df.select("name", "price")     # Cada worker selecciona columnas
df.withColumn("tax", col("price") * 0.15)  # Cálculo local
```

**Wide (con shuffle - LENTO):**
```python
df.groupBy("category").count()  # Requiere mover datos entre workers
df.join(other_df, "id")         # Requiere redistribuir ambos DFs
df.distinct()                   # Requiere comparar todas las particiones
```

#### **3. Shuffle: El Cuello de Botella**
```
ANTES del shuffle:
Worker-1: [Category A: 100, Category B: 50]
Worker-2: [Category A: 80, Category B: 120]

SHUFFLE (redistribuir por key):
Worker-1 envía [Category B: 50] → Worker-2
Worker-2 envía [Category A: 80] → Worker-1

DESPUÉS del shuffle:
Worker-1: [Category A: 180]  ← Suma 100 + 80
Worker-2: [Category B: 170]  ← Suma 50 + 120

🔴 Si Worker-2 muere durante el envío:
  → Worker-1 no recibe [Category A: 80]
  → MetadataFetchFailedException
```

---

## 🚨 Limitaciones de Tu Infraestructura Actual

### **1. Recursos Insuficientes para FP-Growth**

```
TU CLUSTER:
├─ Worker-1: 1 GB RAM, 2 cores
├─ Worker-2: 1 GB RAM, 2 cores
└─ TOTAL:    2 GB RAM, 4 cores

FP-GROWTH con 1M transacciones necesita:
├─ Shuffle data: ~5-10 GB
├─ FP-Tree RAM: ~2-4 GB
└─ Intermediate results: ~2-3 GB
    TOTAL: ~10-15 GB RAM

RESULTADO: 2 GB << 15 GB → CRASH inevitable
```

### **2. Red Interna Docker (Latencia)**
```
Shuffle entre workers:
Container A → Docker Network → Container B

Latencia típica: 1-5 ms
Con millones de operaciones: 1-5 horas de espera solo en red
```

### **3. Disco /tmp Limitado**
```
Cuando RAM se llena, Spark "spills" a disco:
/tmp/spark-shuffle-xxx

Disco container: ~10 GB
Shuffle data: ~20 GB
→ Disk full → Job FAILS
```

---

## 🏭 Cómo se Hace en la Industria

### **Caso Real: Amazon**

```
INFRAESTRUCTURA:
├─ 500+ workers en AWS EMR (Elastic MapReduce)
├─ Cada worker: 32 GB RAM, 8 cores
├─ Red de 10 Gbps entre workers
└─ S3 para almacenamiento (ilimitado)

OPTIMIZACIONES:
1. Pre-filtrado: Solo Top 1000 productos
2. Segmentación: FP-Growth por categoría (no global)
3. Sampling: 1-5% de transacciones (suficiente para patrones)
4. Caching: Redis para resultados frecuentes
5. Incremental: Solo procesar transacciones nuevas
```

### **Caso Real: Netflix**

```
NO USAN FP-GROWTH para recomendaciones!

Usan:
1. Collaborative Filtering (ALS - Alternating Least Squares)
   - Más escalable
   - Menos shuffle
   - Resultados mejores

2. Deep Learning (Transformers)
   - Modelos pre-entrenados
   - Fine-tuning con batch pequeños

3. Graph Databases (Neo4j)
   - Relaciones user-item como grafo
   - Queries rápidas sin shuffle
```

---

## ✅ Soluciones para Tu Proyecto

### **Opción 1: Simplificar (Recomendado para 1M rows)**
```python
# NO hagas FP-Growth completo
# Haz análisis de co-ocurrencia simple:

df_cooccurrence = df_transactions \
    .groupBy("product_a", "product_b") \
    .count() \
    .filter(col("count") > 100) \
    .orderBy("count", descending=True) \
    .limit(100)

# Mucho más rápido, mismos insights
```

### **Opción 2: Aumentar Recursos**
```yaml
# docker-compose.yml
spark-worker-1:
  deploy:
    resources:
      limits:
        memory: 4G  # Aumentar a 4 GB
        cpus: '4'   # Aumentar a 4 cores
```

### **Opción 3: Segmentar + Procesar por Partes**
```python
# train_models.py (modificado)
for category in ["Electronics", "Grocery", "Fashion"]:
    df_category = df_master.filter(col("category") == category)
    
    # FP-Growth solo en esta categoría (más manejable)
    model = FPGrowth(minSupport=0.10).fit(df_category)
    model.save(f"models/fpgrowth_{category}")
```

---

## 📊 Diagrama de Secuencia Completo

```
┌────────┐    ┌─────────┐    ┌───────────┐    ┌──────────┐    ┌─────────┐
│ Usuario│    │ Airflow │    │   Spark   │    │  Spark   │    │  Datos  │
│  Web   │    │ Scheduler│   │   Master  │    │  Workers │    │ (Disk)  │
└───┬────┘    └────┬────┘    └─────┬─────┘    └────┬─────┘    └────┬────┘
    │              │                │                │               │
    │ 1. Trigger  │                │                │               │
    │─────────────>│                │                │               │
    │  DAG Run    │                │                │               │
    │              │                │                │               │
    │              │ 2. Submit Job │                │               │
    │              │───────────────>│                │               │
    │              │                │                │               │
    │              │                │ 3. Assign Tasks│               │
    │              │                │───────────────>│               │
    │              │                │                │               │
    │              │                │                │ 4. Read Data  │
    │              │                │                │──────────────>│
    │              │                │                │               │
    │              │                │                │<──────────────│
    │              │                │                │  CSV/Parquet  │
    │              │                │                │               │
    │              │                │ 5. SHUFFLE     │               │
    │              │                │<──────────────>│               │
    │              │                │  (Data Xfer)   │               │
    │              │                │                │               │
    │              │                │<───────────────│               │
    │              │                │ 6. Results     │               │
    │              │<───────────────│                │               │
    │              │   Job Complete │                │               │
    │<─────────────│                │                │               │
    │ 7. Status OK │                │                │               │
    │              │                │                │               │
```

---

## 📈 Métricas de Tu Sistema Actual

```
CAPACIDAD TEÓRICA:
├─ Throughput: ~10-50 MB/s por worker
├─ Max rows/sec: ~10,000 - 50,000
└─ Processing time: 1M rows en 20-100 segundos (sin shuffle)

CON FP-GROWTH (shuffle intensivo):
├─ Throughput: ~1-5 MB/s (20x más lento)
├─ Max rows: ~50,000 - 100,000 (sin crash)
└─ Processing time: 1M rows → OutOfMemory o 30-60 minutos

RECOMENDACIÓN:
Para 1M rows con FP-Growth:
  Minimum: 8 GB RAM total (4 workers × 2 GB)
  Optimal: 16 GB RAM total (4 workers × 4 GB)
```

---

## 🎯 Conclusión

**Tu infraestructura ESTÁ funcionando correctamente:**
- ✅ Airflow orquesta bien
- ✅ Spark distribuye tareas correctamente
- ✅ Workers ejecutan código en paralelo

**El problema NO es la infraestructura, es el algoritmo:**
- ❌ FP-Growth es inherentemente costoso
- ❌ 1M transacciones es demasiado para 2 GB RAM
- ❌ Shuffle operations saturan la red y memoria

**Soluciones profesionales:**
1. ✅ Sampling (10-20% de datos)
2. ✅ Pre-filtrado (Top-N productos)
3. ✅ Segmentación (por categoría/región)
4. ✅ Algoritmos alternativos (ALS, Graph-based)
5. ✅ Aumentar recursos (4-8 GB por worker)

**Para tu caso (1M rows):**
- Usa sampling al 10% + minSupport=0.10 (actual)
- O usa co-ocurrencia simple en lugar de FP-Growth
- O aumenta RAM a 4 GB por worker si es posible

---

## 📚 Referencias

- [Apache Spark Tuning Guide](https://spark.apache.org/docs/latest/tuning.html)
- [FP-Growth Paper](https://www.cs.sfu.ca/~jpei/publications/sigmod00.pdf)
- [Amazon Recommendations Architecture](https://www.amazon.science/publications)
- [Netflix Recommendations](https://netflixtechblog.com/netflix-recommendations-beyond-the-5-stars-part-1-55838468f429)
