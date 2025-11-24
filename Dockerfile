FROM apache/airflow:2.10.4-python3.10

USER root

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         openjdk-17-jdk-headless \
         procps \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

USER airflow

RUN pip install --no-cache-dir --default-timeout=2000 \
    apache-airflow-providers-apache-spark \
    pyspark==3.5.0