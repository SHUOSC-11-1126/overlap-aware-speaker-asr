"""Module C: Web-based ASR routing analysis API (experimental/frontier)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

from .config import PROJECT_ROOT
from .io_helpers import load_json_dict, read_csv_rows, read_json

# ---------------------------------------------------------------------------
# Table path constants (relative to PROJECT_ROOT)
# ---------------------------------------------------------------------------

CASES_TABLE = "results/tables/current_results_summary.json"
CER_TABLE = "results/tables/cer_results.csv"
ERROR_TYPE_TABLE = "results/tables/error_type_summary.csv"
PERFORMANCE_TABLE = "results/tables/cascade_performance.json"
ROUTING_TABLE = "results/tables/adaptive_routing_results.json"
CPCER_TABLE = "results/tables/cpcer_lite_results.json"
ROBUSTNESS_TABLE = "results/tables/cascade_robustness_gap.json"
RECOMMENDATIONS_TABLE = "results/tables/cascade_recommendations.json"
PARETO_TABLE = "results/tables/cascade_pareto.json"
DECISION_MATRIX_TABLE = "results/tables/cascade_decision_matrix.json"
FAMILY_STABILITY_TABLE = "results/tables/cascade_recommendation_family_stability.json"
STABILITY_TABLE = "results/tables/cascade_recommendation_stability.json"
GLOSSARY_PATH = "resources/glossary/terms.json"

TEMPLATE_DIR = str(PROJECT_ROOT / "demo" / "module_c" / "templates")


def _sanitize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace None values with empty strings for JSON-safe serialization."""
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        cleaned.append({k: ("" if v is None else v) for k, v in row.items()})
    return cleaned

# ---------------------------------------------------------------------------
# Data loader helpers
# ---------------------------------------------------------------------------


def _resolve(path_rel: str) -> Path:
    return PROJECT_ROOT / path_rel


def _load_json_list(path_rel: str) -> list[dict[str, Any]]:
    """Load a JSON list from a project-relative path, returning [] on failure."""
    path = _resolve(path_rel)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and "rows" in data and isinstance(data["rows"], list):
        return [item for item in data["rows"] if isinstance(item, dict)]
    return []


def _load_csv_list(path_rel: str) -> list[dict[str, Any]]:
    """Load a CSV into a list of dicts, returning [] on failure."""
    path = _resolve(path_rel)
    if not path.exists():
        return []
    return read_csv_rows(path, project_root=PROJECT_ROOT)


def _load_cases() -> list[dict[str, Any]]:
    """Return the gold benchmark case summary list."""
    return _load_json_list(CASES_TABLE)


def _load_cer_details() -> list[dict[str, Any]]:
    """Return detailed CER rows for all cases and methods."""
    return _load_csv_list(CER_TABLE)


def _load_error_types() -> list[dict[str, Any]]:
    """Return error-type breakdown rows for all cases and methods."""
    return _load_csv_list(ERROR_TYPE_TABLE)


def _load_performance() -> list[dict[str, Any]]:
    """Return strategy-level performance comparison rows."""
    return _load_json_list(PERFORMANCE_TABLE)


def _load_routing() -> list[dict[str, Any]]:
    """Return per-case adaptive routing decision rows."""
    return _load_json_list(ROUTING_TABLE)


def _load_cpcer() -> list[dict[str, Any]]:
    """Return cpCER-lite speaker attribution rows."""
    return _load_json_list(CPCER_TABLE)


def _load_robustness() -> list[dict[str, Any]]:
    """Return cross-dataset robustness gap rows."""
    return _load_json_list(ROBUSTNESS_TABLE)


def _load_recommendations() -> list[dict[str, Any]]:
    """Return cascade profile-based recommendation rows."""
    return _load_json_list(RECOMMENDATIONS_TABLE)


def _load_pareto() -> list[dict[str, Any]]:
    """Return Pareto frontier rows."""
    return _load_json_list(PARETO_TABLE)


def _load_decision_matrix() -> list[dict[str, Any]]:
    """Return merged cascade decision matrix rows."""
    return _load_json_list(DECISION_MATRIX_TABLE)


def _load_family_stability() -> list[dict[str, Any]]:
    """Return family-level recommendation stability rows."""
    return _load_json_list(FAMILY_STABILITY_TABLE)


def _load_stability() -> list[dict[str, Any]]:
    """Return recommendation stability rows."""
    return _load_json_list(STABILITY_TABLE)


def _load_glossary() -> list[dict[str, Any]]:
    """Return glossary terms from resources."""
    return _load_json_list(GLOSSARY_PATH)


def _find_case(case_id: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find a single case row by case_id."""
    for row in rows:
        if row.get("case_id") == case_id:
            return row
    return None


# ---------------------------------------------------------------------------
# Flask application factory
# ---------------------------------------------------------------------------


def create_app() -> Flask:
    """Create and configure the Module C Flask application."""
    app = Flask(__name__, template_folder=TEMPLATE_DIR)

    @app.after_request
    def _add_cors_headers(response: Any) -> Any:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        return response

    # -- Frontend route -------------------------------------------------------

    @app.route("/")
    def index() -> Any:
        """Serve the Module C single-page frontend."""
        return render_template("index.html")

    # -- API: Case listing ----------------------------------------------------

    @app.route("/api/module_c/cases")
    def api_cases() -> Any:
        """Return the list of gold benchmark cases."""
        cases = _load_cases()
        return jsonify({"cases": cases, "count": len(cases), "label": "experimental/frontier"})

    # -- API: Case detail -----------------------------------------------------

    @app.route("/api/module_c/cases/<case_id>")
    def api_case_detail(case_id: str) -> Any:
        """Return detailed CER and error-type data for a single case."""
        cer_rows = _load_cer_details()
        error_rows = _load_error_types()

        case_cer = [r for r in cer_rows if r.get("case_id") == case_id]
        case_errors = [r for r in error_rows if r.get("case_id") == case_id]

        if not case_cer and not case_errors:
            return jsonify({"error": f"Case '{case_id}' not found."}), 404

        return jsonify(
            {
                "case_id": case_id,
                "cer_details": case_cer,
                "error_types": case_errors,
                "label": "experimental/frontier",
            }
        )

    # -- API: Performance comparison ------------------------------------------

    @app.route("/api/module_c/performance")
    def api_performance() -> Any:
        """Return strategy-level performance comparison data."""
        strategies = _load_performance()
        return jsonify({"strategies": strategies, "count": len(strategies), "label": "experimental/frontier"})

    # -- API: Routing decisions -----------------------------------------------

    @app.route("/api/module_c/routing")
    def api_routing() -> Any:
        """Return per-case routing decisions and strategy summary."""
        routing_rows = _load_routing()
        performance_rows = _load_performance()
        return jsonify(
            {
                "case_decisions": routing_rows,
                "case_count": len(routing_rows),
                "strategy_summary": performance_rows,
                "label": "experimental/frontier",
            }
        )

    # -- API: Risk analysis ---------------------------------------------------

    @app.route("/api/module_c/risk")
    def api_risk() -> Any:
        """Return error profiles, robustness gaps, and cpCER-lite summary."""
        error_rows = _load_error_types()
        robustness_rows = _load_robustness()
        cpcer_rows = _load_cpcer()
        return jsonify(
            {
                "error_profiles": error_rows,
                "robustness_gaps": robustness_rows,
                "cpcer_summary": cpcer_rows,
                "label": "experimental/frontier",
            }
        )

    # -- API: Error types -----------------------------------------------------

    @app.route("/api/module_c/errors")
    def api_errors() -> Any:
        """Return error-type breakdown, optionally filtered by case_id."""
        case_id = request.args.get("case_id", "").strip()
        all_errors = _load_error_types()
        if case_id:
            all_errors = [r for r in all_errors if r.get("case_id") == case_id]
        return jsonify({"errors": all_errors, "count": len(all_errors), "label": "experimental/frontier"})

    # -- API: Cascade recommendations -----------------------------------------

    @app.route("/api/module_c/cascade")
    def api_cascade() -> Any:
        """Return cascade recommendations, Pareto, decision matrix, and stability."""
        recommendations = _sanitize_rows(_load_recommendations())
        pareto = _sanitize_rows(_load_pareto())
        decision_matrix = _sanitize_rows(_load_decision_matrix())
        stability = _sanitize_rows(_load_stability())
        family_stability = _sanitize_rows(_load_family_stability())
        return jsonify(
            {
                "recommendations": recommendations,
                "pareto": pareto,
                "decision_matrix": decision_matrix,
                "stability": stability,
                "family_stability": family_stability,
                "label": "experimental/frontier",
            }
        )

    # -- API: Glossary --------------------------------------------------------

    @app.route("/api/module_c/glossary")
    def api_glossary() -> Any:
        """Return the domain glossary terms."""
        terms = _load_glossary()
        return jsonify({"terms": terms, "count": len(terms), "label": "experimental/frontier"})

    return app


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the Module C API server."""
    parser = argparse.ArgumentParser(description="Module C: ASR Routing Analysis API Server (experimental/frontier)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5100, help="Bind port (default: 5100)")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    return parser.parse_args(argv)


def main() -> None:
    """Run the Module C Flask API server."""
    args = parse_args()
    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
