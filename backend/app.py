from __future__ import annotations

from importlib import import_module

from flask import Flask, jsonify

from .config import load_settings
from .observability import instrument_flask_app
from .routes.websocket import init_websocket, socketio


def create_app() -> Flask:
    app = Flask(__name__)
    settings = load_settings()

    app.config["SECRET_KEY"] = settings.secret_key
    app.config["SETTINGS"] = settings
    instrument_flask_app(app, service_name="query-api")

    health_routes = import_module("backend.routes.health")
    compliance_routes = import_module("backend.routes.compliance")
    ontology_query_routes = import_module("backend.routes.ontology_query")
    ontoflow_query_routes = import_module("backend.ontoflow.query_routes")
    app.register_blueprint(health_routes.health_bp)
    app.register_blueprint(compliance_routes.compliance_bp)
    app.register_blueprint(ontology_query_routes.ontology_query_bp)
    app.register_blueprint(ontoflow_query_routes.ontoflow_query_bp)

    @app.get("/")
    def root():
        return jsonify(
            {
                "name": "Genesis Studio",
                "status": "running",
                "api": "/api/health",
            }
        )

    # Initialize WebSocket
    init_websocket(app)

    return app
