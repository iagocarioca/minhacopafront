from flask import Blueprint, render_template

index_bp = Blueprint("index", __name__)

@index_bp.route("/")
def index():
    """Rota principal do site"""
    return render_template("index.html")

