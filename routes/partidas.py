from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import partida_service as svc
from services import time_service as time_svc
from services import rodada_service as rodada_svc
from services import gol_service as gol_svc
from services.api_client import ApiError

partidas_bp = Blueprint("partidas", __name__)

@partidas_bp.route("/rodadas/<int:rodada_id>/partidas", methods=["GET","POST"])
def list_create(rodada_id: int):
    if request.method == "POST":
        try:
            svc.criar_partida(rodada_id, int(request.form.get("time_casa_id")), int(request.form.get("time_fora_id")))
            flash("Partida criada!", "ok")
        except ApiError as e:
            flash(e.payload.get("erro","Erro ao criar partida"), "error")
        return redirect(url_for("partidas.list_create", rodada_id=rodada_id))

    data = svc.listar_partidas(rodada_id)

    # Buscar times disponíveis através da temporada da rodada
    rodada_data = rodada_svc.obter_rodada(rodada_id)
    rodada = rodada_data.get("rodada", {})
    temporada_id = rodada.get("temporada_id")

    times_disponiveis = []
    if temporada_id:
        times_data = time_svc.listar_times_pelada(temporada_id)
        times_disponiveis = times_data.get("data", [])

    return render_template(
        "partidas/list.html",
        rodada_id=rodada_id,
        temporada_id=temporada_id,
        partidas=data.get("partidas", []),
        times_disponiveis=times_disponiveis,
    )

@partidas_bp.route("/partidas/<int:partida_id>")
def detalhe(partida_id: int):
    data = svc.obter_partida(partida_id).get("partida")
    rodada_id = None
    # enriquecer com times completos (pra ter lista de jogadores nos selects), se possível
    if isinstance(data, dict):
        rodada_id = data.get("rodada_id")
        casa_id = data.get("time_casa_id") or (data.get("time_casa") or {}).get("id")
        fora_id = data.get("time_fora_id") or (data.get("time_fora") or {}).get("id")
        try:
            if casa_id:
                data["time_casa_full"] = time_svc.obter_time(int(casa_id)).get("time")
            if fora_id:
                data["time_fora_full"] = time_svc.obter_time(int(fora_id)).get("time")
        except Exception:
            pass
    return render_template("partidas/detalhe.html", partida=data, rodada_id=rodada_id)

@partidas_bp.route("/partidas/<int:partida_id>/iniciar", methods=["POST"])
def iniciar(partida_id: int):
    try:
        svc.iniciar_partida(partida_id)
        flash("Partida iniciada!", "ok")
    except ApiError as e:
        flash(e.payload.get("erro","Erro ao iniciar"), "error")
    return redirect(url_for("partidas.detalhe", partida_id=partida_id))

@partidas_bp.route("/partidas/<int:partida_id>/finalizar", methods=["POST"])
def finalizar(partida_id: int):
    try:
        svc.finalizar_partida(partida_id)
        flash("Partida finalizada!", "ok")
    except ApiError as e:
        flash(e.payload.get("erro","Erro ao finalizar"), "error")
    return redirect(url_for("partidas.detalhe", partida_id=partida_id))

# HTMX: criar gol e devolver placar + timeline
@partidas_bp.route("/partidas/<int:partida_id>/gol", methods=["POST"])
def htmx_criar_gol(partida_id: int):
    try:
        payload = {
            "time_id": int(request.form.get("time_id")),
            "jogador_id": int(request.form.get("jogador_id")),
            "minuto": int(request.form.get("minuto")) if request.form.get("minuto") else None,
            "gol_contra": True if request.form.get("gol_contra") == "on" else False,
        }
        if request.form.get("assistencia_id"):
            payload["assistencia_id"] = int(request.form.get("assistencia_id"))
        gol_svc.criar_gol(partida_id, payload)
    except ApiError as e:
        # devolve um bloco simples com erro
        return render_template("gols/_error.html", erro=e.payload.get("erro","Erro ao registrar gol")), 400

    partida = svc.obter_partida(partida_id).get("partida")
    return render_template("partidas/_placar_e_timeline.html", partida=partida)

@partidas_bp.route("/gols/<int:gol_id>/delete", methods=["POST"])
def htmx_remover_gol(gol_id: int):
    partida_id = int(request.form.get("partida_id"))
    try:
        gol_svc.remover_gol(gol_id)
    except ApiError as e:
        return render_template("gols/_error.html", erro=e.payload.get("erro","Erro ao remover gol")), 400
    partida = svc.obter_partida(partida_id).get("partida")
    return render_template("partidas/_placar_e_timeline.html", partida=partida)
