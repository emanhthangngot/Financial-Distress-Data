FROM flink:1.20.3-scala_2.12

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-dev \
    && ln -s /usr/bin/python3 /usr/local/bin/python \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir apache-flink==1.20.3 PyYAML==6.0.2 \
    && wget -q -P /opt/flink/lib \
       https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.3.0-1.20/flink-sql-connector-kafka-3.3.0-1.20.jar

RUN mkdir -p /opt/flink/output /opt/flink/checkpoints \
    && chown -R flink:flink /opt/flink/output /opt/flink/checkpoints
USER flink
