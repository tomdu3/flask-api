from flask import Blueprint, jsonify

errors_bp = Blueprint("errors", __name__)


@errors_bp.app_errorhandler(400)
def handle_bad_request(e):
    return jsonify({"error": "Bad request"}), 400


@errors_bp.app_errorhandler(404)
def handle_not_found(e):
    return jsonify({"error": "Resource not found"}), 404


@errors_bp.app_errorhandler(405)
def handle_method_not_allowed(e):
    return jsonify({"error": "HTTP method not allowed"}), 405


@errors_bp.app_errorhandler(500)
def handle_internal_server_error(e):
    return jsonify({"error": "Internal server error occurred"}), 500

