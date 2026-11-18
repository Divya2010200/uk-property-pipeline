FROM apache/airflow:3.4.0-python3.12

USER root
RUN mkdir -p /opt/project/data /opt/pipeline-venv \
    && chown -R airflow:0 /opt/project /opt/pipeline-venv
USER airflow

# The pipeline has its own environment so its packages cannot conflict with Airflow's.
COPY --chown=airflow:0 requirements.txt /opt/project/requirements.txt
RUN python -m venv /opt/pipeline-venv \
    && PIP_USER=false /opt/pipeline-venv/bin/pip install --no-cache-dir -r /opt/project/requirements.txt

COPY --chown=airflow:0 . /opt/project
