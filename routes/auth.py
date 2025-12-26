from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from services.auth_service import login as api_login, register as api_register
from services.api_client import ApiError

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            data = api_login(request.form.get("username","").strip(), request.form.get("senha",""))
            session["access_token"] = data.get("token_acesso")
            session["refresh_token"] = data.get("token_atualizacao")
            return redirect(url_for("peladas.list_create"))
        except ApiError as e:
            flash(e.payload.get("erro","Falha no login"), "error")
    return render_template("auth/login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            email = request.form.get("email","").strip()
            senha = request.form.get("senha","")
            nome = request.form.get("nome","").strip()

            api_register(email, senha, nome)
            flash("Conta criada! Faça login.", "ok")
            return redirect(url_for("auth.login"))
        except ApiError as e:
            flash(e.payload.get("erro","Falha no cadastro"), "error")
    return render_template("auth/register.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
