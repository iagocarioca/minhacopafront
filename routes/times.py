from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from services import time_service as svc
from services import jogador_service as jogador_svc
from services import temporada_service as temp_svc
from services.api_client import ApiError

times_bp = Blueprint("times", __name__)

@times_bp.route("/temporadas/<int:temporada_id>/times", methods=["GET","POST"])
def list_create(temporada_id: int):
    if request.method == "POST":
        try:
            escudo_file = request.files.get("escudo")
            svc.criar_time(
                temporada_id,
                request.form.get("nome","").strip(),
                request.form.get("cor","").strip() or None,
                escudo_file=escudo_file if escudo_file and escudo_file.filename else None
            )
            flash("Time criado!", "ok")
        except ApiError as e:
            flash(e.payload.get("erro","Erro ao criar time"), "error")
        return redirect(url_for("times.list_create", temporada_id=temporada_id))

    data = svc.listar_times_pelada(temporada_id)
    return render_template("times/list.html", temporada_id=temporada_id, times=data.get("data", []))

@times_bp.route("/times/<int:time_id>", methods=["GET","POST"])
def detalhe(time_id: int):
    if request.method == "POST":
        action = request.form.get("action")
        # Verifica se é uma requisição HTMX
        is_htmx = request.headers.get("HX-Request") == "true"
        
        try:
            if action == "add":
                svc.adicionar_jogador(
                    time_id=time_id,
                    jogador_id=int(request.form.get("jogador_id")),
                    capitao=(request.form.get("capitao") == "on"),
                    posicao=request.form.get("posicao","").strip() or None
                )
                if is_htmx:
                    # Retorna apenas a lista de jogadores atualizada
                    time = svc.obter_time(time_id).get("time")
                    return render_template("times/_jogadores_list.html", time=time)
                flash("Jogador adicionado!", "ok")
            elif action == "remove":
                svc.remover_jogador(time_id, int(request.form.get("jogador_id")))
                if is_htmx:
                    # Retorna apenas a lista de jogadores atualizada
                    time = svc.obter_time(time_id).get("time")
                    return render_template("times/_jogadores_list.html", time=time)
                flash("Jogador removido!", "ok")
            elif action == "update":
                # Atualiza a posição do jogador
                jogador_id = int(request.form.get("jogador_id"))
                nova_posicao = request.form.get("posicao", "").strip() or None
                # Busca o jogador atual para manter os outros dados
                time_atual = svc.obter_time(time_id).get("time")
                jogador_atual = None
                if time_atual and time_atual.get("jogadores"):
                    for j in time_atual["jogadores"]:
                        if j.get("id") == jogador_id:
                            jogador_atual = j
                            break
                
                # Remove e readiciona com a nova posição (ou atualiza se houver endpoint específico)
                if jogador_atual:
                    # Remove o jogador
                    svc.remover_jogador(time_id, jogador_id)
                    # Readiciona com a nova posição
                    svc.adicionar_jogador(
                        time_id=time_id,
                        jogador_id=jogador_id,
                        capitao=jogador_atual.get("capitao", False),
                        posicao=nova_posicao
                    )
                
                if is_htmx:
                    # Retorna apenas a lista de jogadores atualizada
                    time = svc.obter_time(time_id).get("time")
                    return render_template("times/_jogadores_list.html", time=time)
                flash("Posição atualizada!", "ok")
            elif action == "update_escudo":
                escudo_file = request.files.get("escudo")
                if escudo_file and escudo_file.filename:
                    svc.atualizar_escudo(time_id, escudo_file)
                    flash("Escudo atualizado!", "ok")
                else:
                    flash("Selecione um arquivo de imagem", "error")
        except ApiError as e:
            if is_htmx:
                # Retorna mensagem de erro para HTMX
                return f'<div class="rounded-md px-4 py-3 text-xs border backdrop-blur-xl bg-rose-50/60 border-rose-300/60 text-rose-800">{e.payload.get("erro","Erro na ação")}</div>', 400
            flash(e.payload.get("erro","Erro na ação"), "error")
        
        if is_htmx:
            return ""  # HTMX já retornou o conteúdo
        return redirect(url_for("times.detalhe", time_id=time_id))

    time = svc.obter_time(time_id).get("time")

    # Get pelada_id through temporada relationship
    pelada_id = None
    temporada_id = None
    jogadores_disponiveis = []
    if isinstance(time, dict) and time.get("temporada_id"):
        temporada_id = time["temporada_id"]
        temporada = temp_svc.obter_temporada(temporada_id).get("temporada", {})
        pelada_id = temporada.get("pelada_id")
        if pelada_id:
            # Lista todos os jogadores da pelada
            todos_jogadores = jogador_svc.listar_jogadores(pelada_id, per_page=200).get("data", [])
            
            # Coleta IDs dos jogadores que já estão em algum time da temporada (incluindo o próprio time)
            jogadores_em_times = set()
            try:
                times_data = svc.listar_times_pelada(temporada_id, per_page=200)
                times_list = times_data.get("data", [])
                
                for t in times_list:
                    # Coleta IDs dos jogadores deste time (incluindo o time atual)
                    # Pode vir em diferentes formatos: lista de dicts, lista de IDs, ou campo time_jogador
                    jogadores_time = []
                    if t.get("jogadores"):
                        jogadores_time = t["jogadores"]
                    elif t.get("time_jogadores"):
                        jogadores_time = t["time_jogadores"]
                    
                    for j in jogadores_time:
                        jogador_id = None
                        if isinstance(j, dict):
                            # Se for dict, pode ter id direto ou aninhado
                            jogador_id = j.get("id") or j.get("jogador_id") or (j.get("jogador", {}).get("id") if isinstance(j.get("jogador"), dict) else None)
                        elif isinstance(j, (int, str)):
                            # Se for direto um ID
                            try:
                                jogador_id = int(j)
                            except (ValueError, TypeError):
                                pass
                        
                        if jogador_id:
                            jogadores_em_times.add(int(jogador_id))
            except Exception as e:
                print(f"[WARN] Erro ao buscar jogadores em times: {e}")
            
            # Filtra jogadores disponíveis (exclui os que já estão em outros times)
            jogadores_disponiveis = [
                j for j in todos_jogadores 
                if j.get("id") and int(j.get("id")) not in jogadores_em_times
            ]

    return render_template("times/detalhe.html", time=time, jogadores_disponiveis=jogadores_disponiveis, temporada_id=temporada_id)
