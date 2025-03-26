from prometheus_client import multiprocess, generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST

from utils.env import set_env_vars
set_env_vars()

from server import create_app, register_blueprint

app = create_app()
app = register_blueprint(app)

registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry)

@app.get("/metrics")
def get_metrics():
    data = generate_latest(registry)
    return data, 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == "__main__":
    app.run(host="127.0.0.1",port=5000, debug=True)