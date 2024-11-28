FROM python:3.11-slim
ENV CONTAINER_HOME=/var/www
WORKDIR $CONTAINER_HOME
ADD requirements.txt .
RUN pip install -r requirements.txt
ADD . $CONTAINER_HOME
RUN mkdir -p /tmp/prometheus

CMD ./start.sh
