from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import rodada_service as svc
from services import time_service as time_svc
from services import temporada_service as temp_svc
from services.api_client import ApiError

rodadas_bp = Blueprint("rodadas", __name__)

@rodadas_bp.route("/temporadas/<int:temporada_id>/rodadas", methods=["GET","POST"])
def list_create(temporada_id: int):
    if request.method == "POST":
        try:
            # Pega os IDs dos times selecionados
            time_ids = request.form.getlist("time_ids")
            time_ids = [int(tid) for tid in time_ids if tid]

            svc.criar_rodada(
                temporada_id,
                request.form.get("data_rodada","").strip(),
                int(request.form.get("quantidade_times","0")),
                int(request.form.get("jogadores_por_time","0")),
                time_ids if time_ids else None
            )
            flash("Rodada criada!", "ok")
        except ApiError as e:
            flash(e.payload.get("erro","Erro ao criar rodada"), "error")
        return redirect(url_for("rodadas.list_create", temporada_id=temporada_id))

    data = svc.listar_rodadas(temporada_id, page=int(request.args.get("page","1")), per_page=10)

    # DEBUG: ver estrutura da resposta
    print(f"[DEBUG] Rodadas data: {data}")

    # Buscar times disponíveis da temporada
    times_data = time_svc.listar_times_pelada(temporada_id)
    times_disponiveis = times_data.get("data", [])

    # Pegar pelada_id para o link de criar times
    temporada = temp_svc.obter_temporada(temporada_id).get("temporada", {})
    pelada_id = temporada.get("pelada_id")

    return render_template("rodadas/list.html", temporada_id=temporada_id, pelada_id=pelada_id, data=data, times_disponiveis=times_disponiveis)

@rodadas_bp.route("/rodadas/<int:rodada_id>")
def detalhe(rodada_id: int):
    data = svc.obter_rodada(rodada_id)
    rodada = data.get("rodada", {})
    
    # Verificar se a rodada tem times na resposta
    # A API pode retornar times em diferentes estruturas
    times_rodada = rodada.get("times", [])
    
    # Se não houver times diretamente, verificar outras possíveis estruturas
    if not times_rodada:
        # Pode estar em data.times ou rodada.data.times
        times_rodada = data.get("times", [])
    
    # Garantir que times seja uma lista
    rodada["times"] = times_rodada if isinstance(times_rodada, list) and len(times_rodada) > 0 else []
    
    # Extrair temporada_id para navegação
    temporada_id = rodada.get("temporada_id")
    
    return render_template("rodadas/detalhe.html", rodada=rodada, temporada_id=temporada_id)
