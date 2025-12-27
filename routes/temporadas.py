from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import temporada_service as svc
from services.api_client import ApiError

temporadas_bp = Blueprint("temporadas", __name__)

@temporadas_bp.route("/peladas/<int:pelada_id>/temporadas", methods=["GET","POST"])
def list_create(pelada_id: int):
    if request.method == "POST":
        try:
            # Convert YYYY-MM to YYYY-MM-01 for API compatibility
            inicio = request.form.get("inicio_mes","").strip()
            fim = request.form.get("fim_mes","").strip()
            if inicio and len(inicio) == 7:  # YYYY-MM format
                inicio = f"{inicio}-01"
            if fim and len(fim) == 7:
                fim = f"{fim}-01"

            svc.criar_temporada(pelada_id, inicio, fim)
            flash("Temporada criada!", "ok")
        except ApiError as e:
            flash(e.payload.get("erro","Erro ao criar temporada"), "error")
        return redirect(url_for("temporadas.list_create", pelada_id=pelada_id))

    data = svc.listar_temporadas(pelada_id, page=int(request.args.get("page","1")), per_page=10)
    return render_template("temporadas/list.html", pelada_id=pelada_id, data=data)

@temporadas_bp.route("/temporadas/<int:temporada_id>", methods=["GET","POST"])
def detalhe(temporada_id: int):
    if request.method == "POST":
        if request.form.get("action") == "encerrar":
            try:
                svc.encerrar_temporada(temporada_id)
                flash("Temporada encerrada!", "ok")
            except ApiError as e:
                flash(e.payload.get("erro","Erro ao encerrar"), "error")
            return redirect(url_for("temporadas.detalhe", temporada_id=temporada_id))

    data = svc.obter_temporada(temporada_id)
    temporada = data.get("temporada", {})
    pelada_id = temporada.get("pelada_id")
    return render_template("temporadas/detalhe.html", temporada=temporada, pelada_id=pelada_id)
