from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, Response
import base64
from services import rodada_service as rodada_svc
from services import votacao_service as svc
from services.api_client import ApiError
from io import BytesIO
import requests
from PIL import Image

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
    # Mapeamento de nomes de posições (normalizados) para ordem de exibição
    ordem_posicoes_nomes = {
        "Goleiro": 1,
        "Zagueiro": 2,
        "Defesa": 3,
        "Lateral": 4,
        "Volante": 5,
        "Meio-campo": 6,
        "Meia": 7,
        "Ataque": 8,
        "Atacante": 8,  # Sinônimo
        "Centroavante": 9,
        "Ponta": 10,
    }
    
    # Mapeamento de posições numéricas para nomes legíveis (fallback)
    posicoes_map_num = {
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
        posicao_nome = None
        posicao_raw = None
        
        # 1. Campo direto "posicao" (pode ser string ou número)
        if "posicao" in j and j["posicao"] is not None:
            posicao_raw = j["posicao"]
        # 2. Campo "posicao_id"
        elif "posicao_id" in j and j["posicao_id"] is not None:
            posicao_raw = j["posicao_id"]
        # 3. Campo aninhado "time_jogador.posicao"
        elif "time_jogador" in j:
            time_jogador = j["time_jogador"]
            if isinstance(time_jogador, dict):
                posicao_raw = time_jogador.get("posicao") or time_jogador.get("posicao_id")
        
        # Processa a posição
        if posicao_raw is not None:
            # Se for string, usa diretamente (normaliza capitalização)
            if isinstance(posicao_raw, str):
                posicao_nome = posicao_raw.strip()
                # Capitaliza primeira letra
                if posicao_nome:
                    posicao_nome = posicao_nome[0].upper() + posicao_nome[1:].lower()
            # Se for número, mapeia para nome
            elif isinstance(posicao_raw, (int, float)):
                posicao_nome = posicoes_map_num.get(int(posicao_raw))
            # Tenta converter para int se for string numérica
            else:
                try:
                    num = int(posicao_raw)
                    posicao_nome = posicoes_map_num.get(num)
                except (ValueError, TypeError):
                    pass
        
        # Ignora jogadores sem posição válida
        if not posicao_nome or posicao_nome.strip() == "":
            print(f"[WARN] Jogador {j.get('id')} ({j.get('apelido') or j.get('nome_completo')}) sem posição válida. Raw: {posicao_raw}, Dados: {j}")
            continue
        
        jogador_data = {
            "id": j.get("id"),
            "nome": j.get("apelido") or j.get("nome_completo", f"Jogador #{j.get('id')}"),
            "time_nome": j.get("time_nome", ""),
            "posicao_nome": posicao_nome,
            "foto_url": j.get("foto_url") or j.get("foto") or None,  # Inclui foto_url se disponível
        }
        
        # Agrupa por posição (usa o nome como chave)
        grouped.setdefault(posicao_nome, []).append(jogador_data)

    # Ordena e retorna lista de tuplas (nome_posicao, [jogadores])
    resultado = []
    for pos_nome, lista in sorted(grouped.items(), key=lambda x: (ordem_posicoes_nomes.get(x[0], 99), x[0])):
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

    votacoes_api = []
    try:
        # 1) tenta listar direto (se a API suportar GET na rota de votações)
        data = svc.listar_votacoes_rodada(rodada_id)
        # compatibilidade com diferentes formatos
        if isinstance(data, list):
            votacoes_api = data
        elif isinstance(data, dict):
            votacoes_api = data.get("votacoes", data.get("data", [])) or []

        # 2) fallback: usa a rota de resultados (esta existe) para descobrir as votações da rodada
        if not votacoes_api:
            res = svc.obter_resultados_rodada(rodada_id, None)
            items = []
            if isinstance(res, list):
                items = res
            elif isinstance(res, dict):
                items = res.get("votacoes", res.get("data", [])) or []

            extracted = []
            for it in (items or []):
                vinfo = None
                if isinstance(it, dict):
                    vinfo = it.get("votacao") if isinstance(it.get("votacao"), dict) else it
                if not isinstance(vinfo, dict):
                    continue
                if vinfo.get("id") is None:
                    continue
                # normaliza campos mais usados no template
                extracted.append({
                    "id": vinfo.get("id"),
                    "rodada_id": vinfo.get("rodada_id", rodada_id),
                    "tipo": vinfo.get("tipo") or vinfo.get("nome") or "Votação",
                    "abre_em": vinfo.get("abre_em"),
                    "fecha_em": vinfo.get("fecha_em"),
                })
            votacoes_api = extracted
    except Exception:
        votacoes_api = []

    return render_template(
        "votacoes/create.html",
        rodada_id=rodada_id,
        created_id=created_id,
        recent_votacoes=session.get("recent_votacoes", []),
        votacoes_api=votacoes_api,
    )

def _buscar_jogador_por_nome(rodada_id: int, nome_busca: str):
    """
    Busca um jogador na rodada pelo nome (flexível, case-insensitive, match parcial).
    Retorna o ID do jogador ou None se não encontrar.
    """
    if not nome_busca or not rodada_id:
        return None
    
    try:
        data = rodada_svc.listar_jogadores_rodada(rodada_id)
        jogadores = data.get("jogadores", [])
        
        nome_busca_lower = nome_busca.lower().strip()
        
        # Primeiro tenta match exato (case-insensitive)
        for j in jogadores:
            apelido = (j.get("apelido") or "").lower().strip()
            nome_completo = (j.get("nome_completo") or "").lower().strip()
            
            if apelido == nome_busca_lower or nome_completo == nome_busca_lower:
                return j.get("id")
        
        # Se não encontrou exato, tenta match parcial (contém)
        for j in jogadores:
            apelido = (j.get("apelido") or "").lower().strip()
            nome_completo = (j.get("nome_completo") or "").lower().strip()
            
            if nome_busca_lower in apelido or nome_busca_lower in nome_completo:
                return j.get("id")
        
        # Se ainda não encontrou, tenta match parcial invertido (nome_busca contém parte do nome)
        for j in jogadores:
            apelido = (j.get("apelido") or "").lower().strip()
            nome_completo = (j.get("nome_completo") or "").lower().strip()
            
            if apelido and apelido in nome_busca_lower:
                return j.get("id")
            if nome_completo and nome_completo in nome_busca_lower:
                return j.get("id")
        
    except Exception as e:
        print(f"[ERROR] Erro ao buscar jogador por nome: {e}")
    
    return None

@votacoes_bp.route("/votacoes/<int:votacao_id>/votar", methods=["GET","POST"])
def votar(votacao_id: int):
    if request.method == "POST":
        try:
            rodada_id = request.args.get("rodada_id")
            try:
                rodada_id = int(rodada_id) if rodada_id else None
            except Exception:
                rodada_id = None
            
            if rodada_id is None:
                rodada_id = _find_rodada_id_for_votacao(votacao_id)
            
            if not rodada_id:
                flash("Não foi possível identificar a rodada. Acesse a votação com ?rodada_id=...", "error")
                return redirect(url_for("votacoes.votar", votacao_id=votacao_id))
            
            # Valida jogador votante (agora por nome)
            votante_nome = request.form.get("jogador_votante_nome", "").strip()
            if not votante_nome:
                flash("Informe seu nome para votar.", "error")
                return redirect(url_for("votacoes.votar", votacao_id=votacao_id, rodada_id=rodada_id))
            
            # Busca o jogador pelo nome (flexível)
            jogador_votante_id = _buscar_jogador_por_nome(rodada_id, votante_nome)
            if not jogador_votante_id:
                flash(f"Não foi possível encontrar um jogador com o nome '{votante_nome}'. Tente usar o nome completo ou apelido.", "error")
                return redirect(url_for("votacoes.votar", votacao_id=votacao_id, rodada_id=rodada_id))
            
            # Valida selecionados (até 3)
            selecionados = request.form.getlist("jogador_votado_ids")
            selecionados = [int(x) for x in selecionados if x]
            if len(selecionados) == 0:
                flash("Selecione pelo menos 1 jogador para votar.", "error")
                return redirect(url_for("votacoes.votar", votacao_id=votacao_id, rodada_id=rodada_id))
            if len(selecionados) > 3:
                flash("Você só pode selecionar até 3 jogadores.", "error")
                return redirect(url_for("votacoes.votar", votacao_id=votacao_id, rodada_id=rodada_id))

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
        
        # Enriquece o ranking com informações de posição dos jogadores (se rodada_id disponível)
        if rodada_id:
            try:
                # Busca todos os jogadores da rodada para pegar posições
                jogadores_rodada = rodada_svc.listar_jogadores_rodada(int(rodada_id))
                jogadores_map = {}
                posicoes_map_num = {
                    1: "Goleiro",
                    2: "Zagueiro", 
                    3: "Lateral",
                    4: "Meia",
                    5: "Atacante"
                }
                
                for j in jogadores_rodada.get("jogadores", []):
                    jog_id = j.get("id")
                    if jog_id:
                        # Pega posição de diferentes campos possíveis
                        posicao_raw = j.get("posicao") or j.get("posicao_id")
                        posicao_final = None
                        
                        if posicao_raw is not None:
                            # Se for string, usa diretamente (normaliza capitalização)
                            if isinstance(posicao_raw, str):
                                posicao_final = posicao_raw.strip()
                                if posicao_final:
                                    posicao_final = posicao_final[0].upper() + posicao_final[1:].lower()
                            # Se for número, mapeia para nome
                            elif isinstance(posicao_raw, (int, float)):
                                posicao_final = posicoes_map_num.get(int(posicao_raw))
                        
                        jogadores_map[jog_id] = {
                            "posicao": posicao_final,
                            "foto_url": j.get("foto_url")
                        }
                
                # Enriquece o ranking com posições
                for item in ranking:
                    jogador = item.get("jogador", {})
                    if jogador and jogador.get("id"):
                        jog_id = jogador.get("id")
                        if jog_id in jogadores_map:
                            jog_info = jogadores_map[jog_id]
                            # Adiciona posição se não existir ou se a existente estiver vazia
                            if jog_info.get("posicao") and (not jogador.get("posicao") or not str(jogador.get("posicao", "")).strip()):
                                jogador["posicao"] = jog_info["posicao"]
                            # Adiciona foto se não existir
                            if not jogador.get("foto_url") and jog_info.get("foto_url"):
                                jogador["foto_url"] = jog_info["foto_url"]
            except Exception as e:
                print(f"[WARN] Erro ao enriquecer ranking com posições: {e}")
        
        # Verifica se a votação está encerrada
        votacao_encerrada = False
        if votacao_info:
            print(f"[DEBUG] votacao_info: {votacao_info}")
            
            # Verifica pelo status
            status = votacao_info.get("status", "")
            if status:
                status_lower = str(status).lower()
                print(f"[DEBUG] Status da votação: {status_lower}")
                if status_lower in ["encerrada", "fechada", "closed", "finalizada"]:
                    votacao_encerrada = True
                    print(f"[DEBUG] Votação encerrada por status: {status_lower}")
            
            # Se não tiver status encerrado, verifica pela data fecha_em
            if not votacao_encerrada and votacao_info.get("fecha_em"):
                from datetime import datetime
                try:
                    fecha_em_str = str(votacao_info.get("fecha_em")).strip()
                    print(f"[DEBUG] Data fecha_em: {fecha_em_str}")
                    if fecha_em_str:
                        # Tenta vários formatos
                        formatos = [
                            '%Y-%m-%d %H:%M:%S',
                            '%Y-%m-%d %H:%M',
                            '%Y-%m-%dT%H:%M:%S',
                            '%Y-%m-%dT%H:%M',
                            '%Y-%m-%d',
                            '%d/%m/%Y %H:%M:%S',
                            '%d/%m/%Y %H:%M',
                            '%d/%m/%Y',
                        ]
                        fecha_em = None
                        for fmt in formatos:
                            try:
                                fecha_em = datetime.strptime(fecha_em_str, fmt)
                                print(f"[DEBUG] Data parseada com formato {fmt}: {fecha_em}")
                                break
                            except ValueError:
                                continue
                        
                        if fecha_em:
                            agora = datetime.now()
                            print(f"[DEBUG] Comparando: {fecha_em} < {agora} = {fecha_em < agora}")
                            if fecha_em < agora:
                                votacao_encerrada = True
                                print(f"[DEBUG] Votação encerrada por data: {fecha_em} < {agora}")
                        else:
                            print(f"[WARN] Não foi possível fazer parse da data: {fecha_em_str}")
                except Exception as e:
                    print(f"[WARN] Erro ao verificar data de encerramento: {e}")
                    import traceback
                    traceback.print_exc()
        
        print(f"[DEBUG] votacao_encerrada final: {votacao_encerrada}")
        
        return render_template(
            "votacoes/resultado.html",
            votacao_id=votacao_id,
            votacao_info=votacao_info,
            ranking=ranking,
            total_votos=total_votos,
            vencedor=vencedor,
            rodada_id=rodada_id,
            votacao_encerrada=votacao_encerrada
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

@votacoes_bp.route("/votacoes/<int:votacao_id>/encerrar", methods=["POST"])
def encerrar(votacao_id: int):
    """Encerra uma votação manualmente"""
    rodada_id = request.args.get("rodada_id")
    try:
        print(f"[DEBUG] Tentando encerrar votação {votacao_id}")
        resultado = svc.encerrar_votacao(votacao_id)
        print(f"[DEBUG] Resposta da API: {resultado}")
        
        # Verifica se a resposta tem mensagem de sucesso
        mensagem = resultado.get("mensagem", "Votação encerrada com sucesso!")
        flash(mensagem, "ok")
    except ApiError as e:
        print(f"[ERROR] Erro ao encerrar votação: {e.status_code} - {e.payload}")
        erro_msg = e.payload.get("erro") if isinstance(e.payload, dict) else str(e.payload)
        
        # Mensagens mais amigáveis para erros comuns
        if e.status_code == 401:
            flash("Você precisa estar autenticado para encerrar a votação", "error")
        elif e.status_code == 403:
            flash("Você não tem permissão para encerrar esta votação. Apenas o dono da pelada pode encerrar.", "error")
        elif e.status_code == 404:
            flash("Votação não encontrada", "error")
        else:
            flash(erro_msg or "Erro ao encerrar votação", "error")
    except Exception as e:
        print(f"[ERROR] Erro inesperado ao encerrar votação: {e}")
        import traceback
        traceback.print_exc()
        flash(f"Erro ao encerrar votação: {str(e)}", "error")
    
    if rodada_id:
        return redirect(url_for("votacoes.resultado", votacao_id=votacao_id, rodada_id=rodada_id))
    return redirect(url_for("votacoes.resultado", votacao_id=votacao_id))

def _download_image(url: str, referer: str = None) -> bytes:
    """Baixa uma imagem de uma URL"""
    headers = {"User-Agent": "Mozilla/5.0 (python-uploader)"}
    if referer:
        headers["Referer"] = referer
    r = requests.get(url, headers=headers, timeout=45, allow_redirects=True)
    r.raise_for_status()
    if not r.content:
        raise RuntimeError(f"Download vazio: {url}")
    return r.content

def _to_png_rgba(img_bytes: bytes) -> bytes:
    """Converte imagem para PNG RGBA"""
    img = Image.open(BytesIO(img_bytes)).convert("RGBA")
    out = BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()

def _resize_mask_to_base(mask_png: bytes, base_png: bytes) -> bytes:
    """Ajusta o tamanho da máscara para o mesmo tamanho da imagem base"""
    base = Image.open(BytesIO(base_png)).convert("RGBA")
    mask = Image.open(BytesIO(mask_png)).convert("RGBA")
    if mask.size != base.size:
        mask = mask.resize(base.size, Image.BILINEAR)
    out = BytesIO()
    mask.save(out, format="PNG", optimize=True)
    return out.getvalue()

@votacoes_bp.route("/votacoes/<int:votacao_id>/gerar-imagem", methods=["POST"])
def gerar_imagem(votacao_id: int):
    """Gera imagem do jogador/goleiro da noite usando n8n"""
    tipo_imagem = request.form.get("tipo")  # "jogador" ou "goleiro"
    rodada_id = request.args.get("rodada_id")
    
    if tipo_imagem not in ["jogador", "goleiro"]:
        flash("Tipo de imagem inválido", "error")
        if rodada_id:
            return redirect(url_for("votacoes.resultado", votacao_id=votacao_id, rodada_id=rodada_id))
        return redirect(url_for("votacoes.resultado", votacao_id=votacao_id))
    
    try:
        # Busca o resultado da votação
        data = svc.obter_resultado(votacao_id)
        ranking = data.get("resultado", [])
        
        if not ranking:
            error_msg = "Não há resultados na votação para gerar imagem"
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "error": error_msg}), 400
            flash(error_msg, "error")
            if rodada_id:
                return redirect(url_for("votacoes.resultado", votacao_id=votacao_id, rodada_id=rodada_id))
            return redirect(url_for("votacoes.resultado", votacao_id=votacao_id))
        
        # Enriquece o ranking com informações de posição dos jogadores (se rodada_id disponível)
        # Isso é necessário para identificar goleiros corretamente
        if rodada_id:
            try:
                jogadores_rodada = rodada_svc.listar_jogadores_rodada(int(rodada_id))
                jogadores_map = {}
                posicoes_map_num = {
                    1: "Goleiro",
                    2: "Zagueiro", 
                    3: "Lateral",
                    4: "Meia",
                    5: "Atacante"
                }
                
                for j in jogadores_rodada.get("jogadores", []):
                    jog_id = j.get("id")
                    if jog_id:
                        posicao_raw = j.get("posicao") or j.get("posicao_id")
                        posicao_final = None
                        
                        if posicao_raw is not None:
                            if isinstance(posicao_raw, str):
                                posicao_final = posicao_raw.strip()
                                if posicao_final:
                                    posicao_final = posicao_final[0].upper() + posicao_final[1:].lower()
                            elif isinstance(posicao_raw, (int, float)):
                                posicao_final = posicoes_map_num.get(int(posicao_raw))
                        
                        jogadores_map[jog_id] = {
                            "posicao": posicao_final,
                            "foto_url": j.get("foto_url")
                        }
                
                # Enriquece o ranking com posições
                for item in ranking:
                    jogador = item.get("jogador", {})
                    if jogador and jogador.get("id"):
                        jog_id = jogador.get("id")
                        if jog_id in jogadores_map:
                            jog_info = jogadores_map[jog_id]
                            if jog_info.get("posicao") and (not jogador.get("posicao") or not str(jogador.get("posicao", "")).strip()):
                                jogador["posicao"] = jog_info["posicao"]
                            if not jogador.get("foto_url") and jog_info.get("foto_url"):
                                jogador["foto_url"] = jog_info["foto_url"]
            except Exception as e:
                print(f"[WARN] Erro ao enriquecer ranking com posições: {e}")
        
        # Filtra e seleciona o mais votado
        jogador_selecionado = None
        item_selecionado = None
        
        if tipo_imagem == "goleiro":
            # Busca o goleiro mais votado (maior total_pontos entre goleiros)
            goleiros = []
            for item in ranking:
                jogador = item.get("jogador", {})
                if not jogador:
                    continue
                
                posicao = jogador.get("posicao", "")
                is_goleiro = False
                
                # Verifica se é goleiro
                if isinstance(posicao, int):
                    if posicao == 1:  # Goleiro
                        is_goleiro = True
                elif isinstance(posicao, str) and posicao.lower() == "goleiro":
                    is_goleiro = True
                
                if is_goleiro:
                    total_pontos = item.get("total_pontos", 0) or 0
                    goleiros.append({
                        "item": item,
                        "jogador": jogador,
                        "total_pontos": total_pontos
                    })
            
            if not goleiros:
                error_msg = "Não há goleiro no resultado da votação"
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"success": False, "error": error_msg}), 400
                flash(error_msg, "error")
                if rodada_id:
                    return redirect(url_for("votacoes.resultado", votacao_id=votacao_id, rodada_id=rodada_id))
                return redirect(url_for("votacoes.resultado", votacao_id=votacao_id))
            
            # Ordena por total_pontos (maior primeiro) e pega o primeiro
            goleiros.sort(key=lambda x: x["total_pontos"], reverse=True)
            item_selecionado = goleiros[0]["item"]
            jogador_selecionado = goleiros[0]["jogador"]
            print(f"[DEBUG] Goleiro mais votado selecionado: {jogador_selecionado.get('apelido') or jogador_selecionado.get('nome_completo')} com {goleiros[0]['total_pontos']} pontos")
        else:
            # Busca o jogador mais votado excluindo goleiros
            jogadores_nao_goleiros = []
            for item in ranking:
                jogador = item.get("jogador", {})
                if not jogador:
                    continue
                
                posicao = jogador.get("posicao", "")
                is_goleiro = False
                
                # Verifica se é goleiro para excluir
                if isinstance(posicao, int):
                    if posicao == 1:  # Goleiro
                        is_goleiro = True
                elif isinstance(posicao, str) and posicao.lower() == "goleiro":
                    is_goleiro = True
                
                if not is_goleiro:
                    total_pontos = item.get("total_pontos", 0) or 0
                    jogadores_nao_goleiros.append({
                        "item": item,
                        "jogador": jogador,
                        "total_pontos": total_pontos
                    })
            
            if not jogadores_nao_goleiros:
                error_msg = "Não há jogadores (excluindo goleiros) no resultado da votação"
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"success": False, "error": error_msg}), 400
                flash(error_msg, "error")
                if rodada_id:
                    return redirect(url_for("votacoes.resultado", votacao_id=votacao_id, rodada_id=rodada_id))
                return redirect(url_for("votacoes.resultado", votacao_id=votacao_id))
            
            # Ordena por total_pontos (maior primeiro) e pega o primeiro
            jogadores_nao_goleiros.sort(key=lambda x: x["total_pontos"], reverse=True)
            item_selecionado = jogadores_nao_goleiros[0]["item"]
            jogador_selecionado = jogadores_nao_goleiros[0]["jogador"]
            print(f"[DEBUG] Jogador mais votado selecionado: {jogador_selecionado.get('apelido') or jogador_selecionado.get('nome_completo')} com {jogadores_nao_goleiros[0]['total_pontos']} pontos")
        
        if not jogador_selecionado:
            flash("Jogador não encontrado no resultado", "error")
            if rodada_id:
                return redirect(url_for("votacoes.resultado", votacao_id=votacao_id, rodada_id=rodada_id))
            return redirect(url_for("votacoes.resultado", votacao_id=votacao_id))
        
        # Pega a URL da foto do jogador
        foto_url = jogador_selecionado.get("foto_url")
        
        # Se não tiver foto no resultado, tenta buscar da rodada
        if not foto_url and rodada_id:
            try:
                jogador_id = jogador_selecionado.get("id")
                if jogador_id:
                    jogadores_rodada = rodada_svc.listar_jogadores_rodada(int(rodada_id))
                    for j in jogadores_rodada.get("jogadores", []):
                        if j.get("id") == jogador_id:
                            foto_url = j.get("foto_url") or j.get("foto")
                            if foto_url:
                                print(f"[DEBUG] Foto encontrada na rodada: {foto_url}")
                                break
            except Exception as e:
                print(f"[WARN] Erro ao buscar foto da rodada: {e}")
        
        # Tenta outros campos possíveis
        if not foto_url:
            foto_url = jogador_selecionado.get("foto") or jogador_selecionado.get("fotoUrl")
        
        if not foto_url:
            print(f"[DEBUG] Jogador selecionado: {jogador_selecionado}")
            flash("Jogador não possui foto cadastrada", "error")
            if rodada_id:
                return redirect(url_for("votacoes.resultado", votacao_id=votacao_id, rodada_id=rodada_id))
            return redirect(url_for("votacoes.resultado", votacao_id=votacao_id))
        
        # Monta URL completa da imagem
        if foto_url.startswith("http"):
            image_1_url = foto_url
        elif foto_url.startswith("/"):
            image_1_url = f"http://192.168.18.162:5001{foto_url}"
        else:
            image_1_url = f"http://192.168.18.162:5001/{foto_url}"
        
        # URL da imagem máscara (fixa)
        IMAGE_2_URL = "https://xvideosgostosas.com/wp-content/uploads/2025/12/Gemini_Generated_Image_ml4n5bml4n5bml4n.png"
        
        # Pega o nome do jogador
        nome_jogador = jogador_selecionado.get("apelido") or jogador_selecionado.get("nome_completo") or "Jogador"
        
        # Configurações do n8n
        WEBHOOK_URL = "https://xai.aurora5.com/v1/gemini-edit-image"
        PROMPT = "faça um edit estilo neon"
        REFERER = "https://xvideosgostosas.com/"
        TIMEOUT = 45
        
        # Baixa as imagens
        print(f"⬇️  Baixando imagens...")
        img1_bytes = _download_image(image_1_url)
        img2_bytes = _download_image(IMAGE_2_URL, REFERER)
        
        # Converte para PNG RGBA
        print(f"🎨 Convertendo para PNG RGBA...")
        base_png = _to_png_rgba(img1_bytes)
        mask_png_raw = _to_png_rgba(img2_bytes)
        
        # Ajusta máscara para o mesmo tamanho
        print(f"📐 Ajustando mask para o mesmo tamanho da imagem base...")
        mask_png = _resize_mask_to_base(mask_png_raw, base_png)
        
        # Prepara arquivos para upload
        files = {
            "image": ("image.png", BytesIO(base_png), "image/png"),
            "mask": ("mask.png", BytesIO(mask_png), "image/png"),
        }
        
        # Payload com nome do jogador
        data = {
            "prompt": PROMPT,
            "nome_jogador": nome_jogador,
            "tipo": tipo_imagem  # "jogador" ou "goleiro"
        }
        
        # Envia para o n8n
        print(f"🚀 Enviando para o n8n...")
        resp = requests.post(
            WEBHOOK_URL,
            files=files,
            data=data,
            timeout=TIMEOUT
        )
        
        print(f"⬅️  Status: {resp.status_code}")
        
        # Verifica se é uma requisição AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            if resp.status_code == 200:
                # O n8n retorna binary, converte para base64
                if resp.content:
                    try:
                        # Tenta detectar se é JSON primeiro
                        try:
                            json_data = resp.json()
                            # Se for JSON, pode ter a imagem em algum campo
                            if isinstance(json_data, dict) and 'image' in json_data:
                                image_data = json_data['image']
                                if isinstance(image_data, str):
                                    # Se já for base64
                                    if image_data.startswith('data:image'):
                                        return jsonify({
                                            "success": True,
                                            "image": image_data
                                        })
                                    else:
                                        # Assume que é base64 sem prefixo
                                        return jsonify({
                                            "success": True,
                                            "image": f"data:image/png;base64,{image_data}"
                                        })
                        except:
                            pass
                        
                        # Se não for JSON, assume que é binary
                        image_base64 = base64.b64encode(resp.content).decode('utf-8')
                        return jsonify({
                            "success": True,
                            "image": f"data:image/png;base64,{image_base64}"
                        })
                    except Exception as e:
                        print(f"[ERROR] Erro ao processar imagem: {e}")
                        return jsonify({
                            "success": False,
                            "error": f"Erro ao processar imagem: {str(e)}"
                        }), 500
                else:
                    return jsonify({
                        "success": False,
                        "error": "Resposta vazia do servidor"
                    }), 500
            else:
                error_msg = "Erro ao gerar imagem"
                try:
                    error_data = resp.json()
                    error_msg = error_data.get("error", error_msg)
                except:
                    error_msg = f"Erro {resp.status_code}: {resp.text[:200]}"
                
                return jsonify({
                    "success": False,
                    "error": error_msg
                }), resp.status_code
        
        # Se não for AJAX, mantém o comportamento antigo
        if resp.status_code == 200:
            flash("Imagem gerada com sucesso!", "ok")
        else:
            flash(f"Erro ao gerar imagem: {resp.status_code}", "error")
        
    except Exception as e:
        print(f"[ERROR] Erro ao gerar imagem: {e}")
        import traceback
        traceback.print_exc()
        
        # Se for AJAX, retorna JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
        
        flash(f"Erro ao gerar imagem: {str(e)}", "error")
    
    if rodada_id:
        return redirect(url_for("votacoes.resultado", votacao_id=votacao_id, rodada_id=rodada_id))
    return redirect(url_for("votacoes.resultado", votacao_id=votacao_id))
