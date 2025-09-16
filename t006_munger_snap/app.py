"""Flask entry point for Munger Snap."""
from __future__ import annotations

from flask import Flask, render_template, request

from .logic import four_filters


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    def index() -> str:
        return render_template(
            "index.html",
            result=None,
            thesis="",
            pe_input="",
            fcf_input="",
            error=None,
            char_count=0,
        )

    @app.route("/snap", methods=["POST"])
    def snap() -> str:
        thesis = request.form.get("thesis", "").strip()
        pe_input = request.form.get("pe", "").strip()
        fcf_input = request.form.get("fcf_yield", "").strip()

        error = None
        if not thesis:
            error = "Add a brief 6–10 line thesis to score."
        elif len(thesis) > 1200:
            error = "Trim input to 1,200 characters."

        result = None
        if error is None:
            result = four_filters(thesis, pe_input or None, fcf_input or None)

        return render_template(
            "index.html",
            result=result,
            thesis=thesis,
            pe_input=pe_input,
            fcf_input=fcf_input,
            error=error,
            char_count=len(thesis),
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
