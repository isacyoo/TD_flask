#!/bin/bash

echo Prometheus multiproc dir: ${PROMETHEUS_MULTIPROC_DIR}
if [ -z ${PROMETHEUS_MULTIPROC_DIR} ]; then
    echo Prometheus multi proc dir is not configured
    echo Set it to default value of /tmp/prometheus
    export PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
fi
if [ -d ${PROMETHEUS_MULTIPROC_DIR} ]; then
    echo "Found prometheus multiproc directory"
    if [ "$(ls -A ${PROMETHEUS_MULTIPROC_DIR})" ]; then
        rm -r ${PROMETHEUS_MULTIPROC_DIR}/*
        echo "Removed old prometheus multiproc files"
    fi
else
    mkdir ${PROMETHEUS_MULTIPROC_DIR}
    echo "Created prometheus multiproc directory"
fi

echo "Starting gunicorn"
gunicorn -b :5000 --pythonpath /var/www app:app --workers `nproc` --threads 1 --config=gunicorn_config.py