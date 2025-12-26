from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services import rodada_service as rodada_svc
from services import votacao_service as svc
from services.api_client import ApiError

votacoes_bp = Blueprint("votacoes", __name__)

def _extract_votacao_id(payload: dict | None):
    if not isinstance(payload, dict):
        return None
    return (
        (payload.get("votacao") or {}).get("id")
        or payload.get("votacao_id")
        or payload.get("id")
    )

def _find_rodada_id_for_votacao(votacao_id: int) -> int | None:
    recent = session.get("recent_votacoes", [])
    if not isinstance(recent, list):
        return None
    for it in recent:
        try:
            if int((it or {}).get("id")) == int(votacao_id):
                rid = (it or {}).get("rodada_id")
                return int(rid) if rid is not None else None
        except Exception:
            continue
    return None

def _collect_jogadores_por_posicao(rodada_id: int):
    """
    Monta lista de jogadores disponíveis na rodada, agrupados por posição.
    Agora usa a nova rota GET /api/peladas/rodadas/{rodada_id}/jogadores
    """
    # Mapeamento de posições numéricas para nomes legíveis
    posicoes_map = {
        1: "Goleiro",
        2: "Defesa",
        3: "Meio-campo",
        4: "Ataque",
        5: "Lateral",
        6: "Volante",
        7: "Meia",
        8: "Centroavante",
        9: "Ponta",
        10: "Zagueiro"
    }
    
    # Ordem de exibição das posições
    ordem_posicoes = {
        1: 1,   # Goleiro
        10: 2,  # Zagueiro
        2: 3,   # Defesa
        5: 4,   # Lateral
        6: 5,   # Volante
        3: 6,   # Meio-campo
        7: 7,   # Meia
        4: 8,   # Ataque
        8: 9,   # Centroavante
        9: 10,  # Ponta
    }
    
    try:
        data = rodada_svc.listar_jogadores_rodada(rodada_id)
        jogadores = data.get("jogadores", [])
        print(f"[DEBUG] Jogadores da rodada {rodada_id}: {len(jogadores)} jogadores")
        if jogadores:
            print(f"[DEBUG] Exemplo de jogador: {jogadores[0]}")
    except Exception as e:
        print(f"[ERROR] Erro ao buscar jogadores da rodada: {e}")
        return []

    # Agrupa por posição
    grouped = {}
    for j in jogadores:
        # Tenta pegar posição de diferentes campos possíveis
        posicao_num = None
        
        # 1. Campo direto "posicao"
        if "posicao" in j and j["posicao"] is not None:
            posicao_num = j["posicao"]
        # 2. Campo "posicao_id"
        elif "posicao_id" in j and j["posicao_id"] is not None:
            posicao_num = j["posicao_id"]
        # 3. Campo aninhado "time_jogador.posicao"
        elif "time_jogador" in j:
            time_jogador = j["time_jogador"]
            if isinstance(time_jogador, dict):
                posicao_num = time_jogador.get("posicao") or time_jogador.get("posicao_id")
        
        # Converte para int se necessário
        if posicao_num is not None:
            try:
                posicao_num = int(posicao_num)
            except (ValueError, TypeError):
                posicao_num = None
        
        # Mapeia para nome legível
        posicao_nome = posicoes_map.get(posicao_num, f"Posição {posicao_num}" if posicao_num else "Sem posição")
        
        jogador_data = {
            "id": j.get("id"),
            "nome": j.get("apelido") or j.get("nome_completo", f"Jogador #{j.get('id')}"),
            "time_nome": j.get("time_nome", ""),
            "posicao": posicao_num,  # Guarda a posição numérica também
            "posicao_nome": posicao_nome,  # Guarda o nome da posição
        }
        
        # Agrupa por posição (usa 999 para "Sem posição" para aparecer no final)
        pos_key = (posicao_num if posicao_num is not None else 999, posicao_nome)
        grouped.setdefault(pos_key, []).append(jogador_data)
        
        # Debug para verificar posição
        if posicao_num is None:
            print(f"[WARN] Jogador {j.get('id')} ({j.get('apelido') or j.get('nome_completo')}) sem posição. Dados: {j}")

    # Ordena e retorna lista de tuplas (nome_posicao, [jogadores])
    resultado = []
    for (pos_num, pos_nome), lista in sorted(grouped.items(), key=lambda x: (ordem_posicoes.get(x[0][0], 99), x[0][1])):
        resultado.append((pos_nome, sorted(lista, key=lambda x: x["nome"].lower())))
    
    return resultado

@votacoes_bp.route("/rodadas/<int:rodada_id>/votacoes", methods=["GET","POST"])
def criar(rodada_id: int):
    if request.method == "POST":
        try:
            resp = svc.criar_votacao(
                rodada_id,
                request.form.get("abre_em","").strip(),
                request.form.get("fecha_em","").strip(),
                request.form.get("tipo","").strip()
            )
            votacao_id = _extract_votacao_id(resp)
            flash("Votação criada!", "ok")
        except ApiError as e:
            flash(e.payload.get("erro","Erro ao criar votação"), "error")
            return redirect(url_for("votacoes.criar", rodada_id=rodada_id))

        # guarda um histórico curto pra ficar "registrado" na tela
        if votacao_id:
            recent = session.get("recent_votacoes", [])
            if not isinstance(recent, list):
                recent = []
            recent.insert(0, {
                "id": int(votacao_id),
                "rodada_id": int(rodada_id),
                "tipo": (request.form.get("tipo","").strip() or "Votação"),
                "abre_em": request.form.get("abre_em","").strip(),
                "fecha_em": request.form.get("fecha_em","").strip(),
            })
            # remove duplicadas por id, mantendo a primeira ocorrência
            seen = set()
            dedup = []
            for it in recent:
                _id = (it or {}).get("id")
                if _id in seen:
                    continue
                seen.add(_id)
                dedup.append(it)
            session["recent_votacoes"] = dedup[:5]
            return redirect(url_for("votacoes.criar", rodada_id=rodada_id, created=votacao_id))

        return redirect(url_for("votacoes.criar", rodada_id=rodada_id))

    created = request.args.get("created")
    created_id = None
    try:
        created_id = int(created) if created else None
    except Exception:
        created_id = None

    return render_template(
        "votacoes/create.html",
        rodada_id=rodada_id,
        created_id=created_id,
        recent_votacoes=session.get("recent_votacoes", []),
    )

@votacoes_bp.route("/votacoes/<int:votacao_id>/votar", methods=["GET","POST"])
def votar(votacao_id: int):
    if request.method == "POST":
        try:
            # Valida jogador votante
            votante_str = request.form.get("jogador_votante_id", "").strip()
            if not votante_str:
                flash("Informe seu ID de jogador para votar.", "error")
                return redirect(url_for("votacoes.votar", votacao_id=votacao_id, rodada_id=request.args.get("rodada_id")))
            
            try:
                jogador_votante_id = int(votante_str)
            except ValueError:
                flash("ID do jogador deve ser um número válido.", "error")
                return redirect(url_for("votacoes.votar", votacao_id=votacao_id, rodada_id=request.args.get("rodada_id")))
            
            # Valida selecionados (até 3)
            selecionados = request.form.getlist("jogador_votado_ids")
            selecionados = [int(x) for x in selecionados if x]
            if len(selecionados) == 0:
                flash("Selecione pelo menos 1 jogador para votar.", "error")
                return redirect(url_for("votacoes.votar", votacao_id=votacao_id, rodada_id=request.args.get("rodada_id")))
            if len(selecionados) > 3:
                flash("Você só pode selecionar até 3 jogadores.", "error")
                return redirect(url_for("votacoes.votar", votacao_id=votacao_id, rodada_id=request.args.get("rodada_id")))

            # Registra votos
            for jid in selecionados:
                svc.votar(votacao_id, jogador_votante_id, jid, 1)

            flash(f"Voto registrado! {len(selecionados)} jogador(es) selecionado(s).", "ok")
        except ApiError as e:
            erro_msg = e.payload.get("erro","Erro ao votar")
            # Mensagem mais amigável para votação fechada
            if "não está aberta" in erro_msg.lower():
                flash("⏰ Esta votação não está aberta no momento. Verifique o período de votação.", "error")
            else:
                flash(erro_msg, "error")
        
        rodada_id = request.args.get("rodada_id")
        return redirect(url_for("votacoes.votar", votacao_id=votacao_id, rodada_id=rodada_id) if rodada_id else url_for("votacoes.votar", votacao_id=votacao_id))

    # GET
    rodada_id = request.args.get("rodada_id")
    try:
        rodada_id = int(rodada_id) if rodada_id else None
    except Exception:
        rodada_id = None
    if rodada_id is None:
        rodada_id = _find_rodada_id_for_votacao(votacao_id)

    posicoes = []
    if rodada_id:
        try:
            posicoes = _collect_jogadores_por_posicao(int(rodada_id))
        except Exception:
            posicoes = []

    # Tenta buscar informações da votação para debug
    votacao_info = None
    try:
        votacao_data = svc.obter_votacao(votacao_id)
        if votacao_data:
            votacao_info = votacao_data.get("votacao", {})
    except Exception:
        pass

    return render_template("votacoes/votar.html", votacao_id=votacao_id, rodada_id=rodada_id, posicoes=posicoes, votacao_info=votacao_info)

@votacoes_bp.route("/votacoes/<int:votacao_id>/resultado")
def resultado(votacao_id: int):
    """Mostra o resultado/ranking de uma votação específica"""
    rodada_id = request.args.get("rodada_id")
    
    try:
        data = svc.obter_resultado(votacao_id)
        
        # Estrutura do retorno da API (compatibilidade):
        # {
        #   "total_votos": int,              <- Topo (novo)
        #   "resultado": [...],              <- Topo (novo)
        #   "vencedor": {...},               <- Topo (novo)
        #   "votacao": {                     <- Aninhado (compatibilidade)
        #     "total_votos": int,
        #     "resultado": [...],
        #     "vencedor": {...}
        #   }
        # }
        
        ranking = data.get("resultado", [])
        total_votos = data.get("total_votos", 0)
        vencedor = data.get("vencedor")
        
        # Info da votação (tipo, datas, etc)
        votacao_info = data.get("votacao", {})
        
        # Tenta pegar rodada_id da sessão se não vier no resultado ou da URL
        if not rodada_id:
            rodada_id = votacao_info.get("rodada_id")
        if not rodada_id:
            rodada_id = _find_rodada_id_for_votacao(votacao_id)
        
        return render_template(
            "votacoes/resultado.html",
            votacao_id=votacao_id,
            votacao_info=votacao_info,
            ranking=ranking,
            total_votos=total_votos,
            vencedor=vencedor,
            rodada_id=rodada_id
        )
    except ApiError as e:
        flash(e.payload.get("erro","Erro ao carregar resultado da votação"), "error")
        # Tenta voltar pra criar votação da rodada, se tiver rodada_id
        if rodada_id:
            try:
                return redirect(url_for("votacoes.criar", rodada_id=int(rodada_id)))
            except:
                pass
        # Senão, vai pra página inicial
        return redirect("/")

@votacoes_bp.route("/rodadas/<int:rodada_id>/votacoes/resultados")
def resultados_rodada(rodada_id: int):
    """Mostra resultados de TODAS as votações de uma rodada"""
    tipo_filtro = request.args.get("tipo")
    
    try:
        data = svc.obter_resultados_rodada(rodada_id, tipo_filtro)
        print(f"[DEBUG] Resultados rodada API response: {type(data)} - {data}")
        
        # Estrutura do retorno da API:
        # {
        #   "votacoes": [
        #     {
        #       "votacao": {...},
        #       "total_votos": int,
        #       "resultado": [...],
        #       "vencedor": {...}
        #     }
        #   ]
        # }
        
        # Se a API retornar uma lista diretamente
        if isinstance(data, list):
            votacoes = data
        # Se retornar um dicionário com a chave "votacoes"
        elif isinstance(data, dict):
            votacoes = data.get("votacoes", [])
        else:
            votacoes = []
        
        print(f"[DEBUG] Resultados rodada - total votacoes: {len(votacoes)}")
        
        return render_template(
            "votacoes/resultados_rodada.html",
            rodada_id=rodada_id,
            votacoes=votacoes,
            tipo_filtro=tipo_filtro
        )
    except ApiError as e:
        print(f"[ERROR API] Resultados rodada: {e.payload}")
        flash(e.payload.get("erro","Erro ao carregar resultados da rodada"), "error")
        return redirect(url_for("votacoes.criar", rodada_id=rodada_id))
    except Exception as e:
        print(f"[ERROR] Resultados rodada: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return render_template(
            "votacoes/resultados_rodada.html",
            rodada_id=rodada_id,
            votacoes=[],
            tipo_filtro=tipo_filtro
        )
