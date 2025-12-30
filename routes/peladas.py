from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import pelada_service as svc
from services.api_client import ApiError
import unicodedata
import re

peladas_bp = Blueprint("peladas", __name__, url_prefix="")

def criar_slug(texto):
    """Converte texto para slug (URL-friendly)"""
    # Remove acentos
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    # Converte para minúsculas
    texto = texto.lower()
    # Remove caracteres especiais, mantém apenas letras, números e espaços
    texto = re.sub(r'[^a-z0-9\s-]', '', texto)
    # Substitui espaços por hífens
    texto = re.sub(r'\s+', '-', texto.strip())
    # Remove hífens múltiplos
    texto = re.sub(r'-+', '-', texto)
    return texto

def buscar_pelada_por_nome(nome_slug):
    """Busca pelada pelo nome (slug)"""
    # Lista todas as peladas e busca pelo nome correspondente
    page = 1
    while True:
        try:
            data = svc.listar_peladas(page=page, per_page=50)
            peladas = data.get("data", [])
            
            for pelada in peladas:
                pelada_nome = pelada.get("nome", "")
                if criar_slug(pelada_nome) == nome_slug:
                    return pelada
            
            # Verifica se há mais páginas
            meta = data.get("meta", {})
            if page >= meta.get("total_pages", 1):
                break
            page += 1
        except Exception:
            break
    
    return None

@peladas_bp.route("/peladas", methods=["GET", "POST"])
def list_create():
    if request.method == "POST":
        try:
            logo_file = request.files.get("logo")
            perfil_file = request.files.get("perfil")
            # Verificar se há arquivos válidos
            has_logo = logo_file and logo_file.filename and logo_file.filename.strip()
            has_perfil = perfil_file and perfil_file.filename and perfil_file.filename.strip()
            
            svc.criar_pelada(
                nome=request.form.get("nome","").strip(),
                cidade=request.form.get("cidade","").strip(),
                fuso_horario=request.form.get("fuso_horario","").strip() or None,
                logo_file=logo_file if has_logo else None,
                perfil_file=perfil_file if has_perfil else None
            )
            flash("Pelada criada!", "ok")
        except ApiError as e:
            flash(e.payload.get("erro","Erro ao criar pelada"), "error")
        return redirect(url_for("peladas.list_create"))

    page = int(request.args.get("page", "1"))
    data = svc.listar_peladas(page=page, per_page=10)
    
    # Filtrar peladas que o usuário realmente pode acessar
    # Busca o ID do usuário logado para comparar com usuario_gerente_id
    from services.auth_service import me
    from services.api_client import ApiError
    
    usuario_id = None
    try:
        usuario_data = me()
        usuario_id = usuario_data.get("usuario", {}).get("id") if isinstance(usuario_data, dict) else None
    except ApiError:
        pass  # Se não conseguir buscar, filtra por tentativa de acesso
    
    peladas_validas = []
    if data and data.get("data"):
        for pelada in data.get("data", []):
            # Se temos o ID do usuário, verifica se ele é o gerente
            if usuario_id and pelada.get("usuario_gerente_id"):
                if pelada.get("usuario_gerente_id") == usuario_id:
                    peladas_validas.append(pelada)
                # Se não for o gerente, não adiciona
            else:
                # Se não temos o ID ou a pelada não tem usuario_gerente_id, 
                # tenta acessar o perfil para verificar permissão
                try:
                    svc.perfil_pelada(pelada.get("id"))
                    peladas_validas.append(pelada)
                except ApiError as e:
                    # Se der 403, não adiciona (usuário não tem acesso)
                    if e.status_code != 403:
                        # Outros erros, adiciona mesmo assim
                        peladas_validas.append(pelada)
    
    # Atualiza os dados com apenas as peladas válidas
    if peladas_validas:
        data["data"] = peladas_validas
        # Ajusta metadados
        if "meta" in data:
            data["meta"]["total"] = len(peladas_validas)
            data["meta"]["total_pages"] = max(1, (len(peladas_validas) + data["meta"].get("per_page", 10) - 1) // data["meta"].get("per_page", 10))
    else:
        # Se não houver peladas válidas, garante estrutura vazia
        data["data"] = []
        if "meta" in data:
            data["meta"]["total"] = 0
            data["meta"]["total_pages"] = 0
    
    return render_template("peladas/list.html", data=data)

@peladas_bp.route("/peladas/<int:pelada_id>")
def perfil(pelada_id: int):
    data = svc.perfil_pelada(pelada_id)
    # Debug: verificar se logo_url está presente
    if data.get("pelada"):
        pelada = data['pelada']
        print(f"[DEBUG] Pelada {pelada_id} - logo_url: {pelada.get('logo_url')}")
        print(f"[DEBUG] Pelada {pelada_id} - perfil_url: {pelada.get('perfil_url')}")
        print(f"[DEBUG] Pelada {pelada_id} - dados completos: {pelada}")
    return render_template("peladas/perfil.html", **data)

@peladas_bp.route("/peladas/<int:pelada_id>/scout-anual")
def scout_anual(pelada_id: int):
    """Scout anual consolidado de todas as temporadas da pelada"""
    from services import temporada_service as temp_svc, ranking_service as rank_svc, time_service as time_svc
    from services.api_client import ApiError
    
    try:
        # Busca dados da pelada
        pelada_data = svc.perfil_pelada(pelada_id)
        pelada = pelada_data.get("pelada", {})
        
        # Busca todas as temporadas (com paginação)
        todas_temporadas = []
        page = 1
        while True:
            try:
                data = temp_svc.listar_temporadas(pelada_id, page=page, per_page=100)
                temporadas = data.get("data", [])
                todas_temporadas.extend(temporadas)
                
                meta = data.get("meta", {})
                if page >= meta.get("total_pages", 1):
                    break
                page += 1
            except Exception as e:
                print(f"[WARN] Erro ao buscar temporadas (página {page}): {e}")
                break
        
        # Agrega dados de todas as temporadas
        ranking_gols_consolidado = {}  # {jogador_id: {"jogador": {...}, "total_gols": X}}
        ranking_assistencias_consolidado = {}  # {jogador_id: {"jogador": {...}, "total_assistencias": X}}
        titulos_jogadores = {}  # {jogador_id: quantidade_titulos}
        
        for temporada in todas_temporadas:
            temporada_id = temporada.get("id")
            if not temporada_id:
                continue
            
            try:
                # Ranking de artilheiros
                artilheiros_data = rank_svc.ranking_artilheiros(temporada_id, limit=1000)
                if isinstance(artilheiros_data, list):
                    ranking_artilheiros = artilheiros_data
                elif isinstance(artilheiros_data, dict):
                    ranking_artilheiros = artilheiros_data.get("ranking", [])
                else:
                    ranking_artilheiros = []
                
                for item in ranking_artilheiros:
                    jogador = item.get("jogador", {}) if isinstance(item, dict) else {}
                    jogador_id = jogador.get("id") if isinstance(jogador, dict) else None
                    if not jogador_id:
                        continue
                    
                    gols = (jogador.get("total_gols") if isinstance(jogador, dict) else None) or item.get("gols") or item.get("total_gols") or 0
                    gols = int(gols) if gols else 0
                    
                    if jogador_id not in ranking_gols_consolidado:
                        ranking_gols_consolidado[jogador_id] = {
                            "jogador": jogador,
                            "total_gols": 0
                        }
                    ranking_gols_consolidado[jogador_id]["total_gols"] += gols
                
                # Ranking de assistências
                assistencias_data = rank_svc.ranking_assistencias(temporada_id, limit=1000)
                if isinstance(assistencias_data, list):
                    ranking_assistencias = assistencias_data
                elif isinstance(assistencias_data, dict):
                    ranking_assistencias = assistencias_data.get("ranking", [])
                else:
                    ranking_assistencias = []
                
                for item in ranking_assistencias:
                    jogador = item.get("jogador", {}) if isinstance(item, dict) else {}
                    jogador_id = jogador.get("id") if isinstance(jogador, dict) else None
                    if not jogador_id:
                        continue
                    
                    assistencias = (jogador.get("total_assistencias") if isinstance(jogador, dict) else None) or item.get("assistencias") or item.get("total_assistencias") or 0
                    assistencias = int(assistencias) if assistencias else 0
                    
                    if jogador_id not in ranking_assistencias_consolidado:
                        ranking_assistencias_consolidado[jogador_id] = {
                            "jogador": jogador,
                            "total_assistencias": 0
                        }
                    ranking_assistencias_consolidado[jogador_id]["total_assistencias"] += assistencias
                
                # Time campeão (primeiro lugar)
                times_data = rank_svc.ranking_times(temporada_id)
                if isinstance(times_data, list):
                    ranking_times = times_data
                elif isinstance(times_data, dict):
                    ranking_times = times_data.get("ranking", [])
                else:
                    ranking_times = []
                
                if ranking_times and len(ranking_times) > 0:
                    primeiro_lugar = ranking_times[0]
                    time_campeao = primeiro_lugar.get("time", {}) if isinstance(primeiro_lugar, dict) else primeiro_lugar
                    
                    if time_campeao and time_campeao.get("id"):
                        try:
                            time_data = time_svc.obter_time(time_campeao["id"])
                            if isinstance(time_data, dict):
                                time_full = time_data.get("time", time_data)
                                jogadores_time = time_full.get("jogadores", []) if isinstance(time_full, dict) else []
                                
                                for jogador in jogadores_time:
                                    jogador_id = jogador.get("id")
                                    if jogador_id:
                                        titulos_jogadores[jogador_id] = titulos_jogadores.get(jogador_id, 0) + 1
                        except Exception as e:
                            print(f"[WARN] Erro ao buscar jogadores do time campeão (temp {temporada_id}): {e}")
            
            except Exception as e:
                print(f"[WARN] Erro ao processar temporada {temporada_id}: {e}")
                continue
        
        # Ordena rankings
        ranking_gols_final = sorted(
            ranking_gols_consolidado.values(),
            key=lambda x: x["total_gols"],
            reverse=True
        )
        
        ranking_assistencias_final = sorted(
            ranking_assistencias_consolidado.values(),
            key=lambda x: x["total_assistencias"],
            reverse=True
        )
        
        # Ranking de títulos (jogadores com mais títulos) - agrupado por quantidade
        ranking_titulos_por_qtd = {}  # {qtd_titulos: [lista de jogadores]}
        for jogador_id, qtd_titulos in titulos_jogadores.items():
            # Busca dados do jogador (pega de qualquer ranking)
            jogador_data = None
            if jogador_id in ranking_gols_consolidado:
                jogador_data = ranking_gols_consolidado[jogador_id]["jogador"]
            elif jogador_id in ranking_assistencias_consolidado:
                jogador_data = ranking_assistencias_consolidado[jogador_id]["jogador"]
            
            if jogador_data:
                if qtd_titulos not in ranking_titulos_por_qtd:
                    ranking_titulos_por_qtd[qtd_titulos] = []
                ranking_titulos_por_qtd[qtd_titulos].append({
                    "jogador": jogador_data,
                    "total_titulos": qtd_titulos
                })
        
        # Ordena por quantidade de títulos (decrescente) e converte para lista de grupos
        ranking_titulos = []
        for qtd in sorted(ranking_titulos_por_qtd.keys(), reverse=True):
            ranking_titulos.append({
                "total_titulos": qtd,
                "jogadores": ranking_titulos_por_qtd[qtd]
            })
        
        return render_template(
            "peladas/scout_anual.html",
            pelada_id=pelada_id,
            pelada=pelada,
            ranking_gols=ranking_gols_final,
            ranking_assistencias=ranking_assistencias_final,
            ranking_titulos=ranking_titulos,
            total_temporadas=len(todas_temporadas)
        )
    
    except Exception as e:
        print(f"[ERROR] Scout anual: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return render_template(
            "peladas/scout_anual.html",
            pelada_id=pelada_id,
            pelada={},
            ranking_gols=[],
            ranking_assistencias=[],
            ranking_titulos=[],
            total_temporadas=0
        )

@peladas_bp.route("/peladas/<int:pelada_id>/publico")
def perfil_publico(pelada_id: int):
    """Perfil público da pelada - sem autenticação necessária (rota legada com ID)"""
    from services import pelada_service, ranking_service
    from services.api_client import ApiError
    
    try:
        # Buscar dados da pelada
        pelada_data = pelada_service.perfil_pelada(pelada_id)
        pelada = pelada_data.get("pelada", {})
        temporada_ativa = pelada_data.get("temporada_ativa")
        
        # Buscar rankings se houver temporada ativa
        ranking_times = []
        ranking_artilheiros = []
        ranking_assistencias = []
        
        if temporada_ativa and temporada_ativa.get("id"):
            temporada_id = temporada_ativa["id"]
            
            # Ranking de times
            try:
                data_times = ranking_service.ranking_times(temporada_id)
                print(f"[DEBUG] Ranking times (ID {pelada_id}): {type(data_times)}")
                if isinstance(data_times, list):
                    ranking_times = data_times
                elif isinstance(data_times, dict):
                    ranking_times = data_times.get("ranking", data_times.get("data", []))
                if ranking_times and len(ranking_times) > 0:
                    print(f"[DEBUG] First time item: {ranking_times[0]}")
            except Exception as e:
                print(f"[ERROR] Ranking times: {e}")
                import traceback
                traceback.print_exc()
                ranking_times = []
            
            # Ranking de artilheiros
            try:
                data_art = ranking_service.ranking_artilheiros(temporada_id, limit=10)
                print(f"[DEBUG] Ranking artilheiros (ID {pelada_id}): {type(data_art)}")
                if isinstance(data_art, list):
                    ranking_artilheiros = data_art
                elif isinstance(data_art, dict):
                    ranking_artilheiros = data_art.get("ranking", data_art.get("data", []))
                if ranking_artilheiros and len(ranking_artilheiros) > 0:
                    print(f"[DEBUG] First artilheiro item: {ranking_artilheiros[0]}")
            except Exception as e:
                print(f"[ERROR] Ranking artilheiros: {e}")
                import traceback
                traceback.print_exc()
                ranking_artilheiros = []
            
            # Ranking de assistências
            try:
                data_ass = ranking_service.ranking_assistencias(temporada_id, limit=10)
                print(f"[DEBUG] Ranking assistencias (ID {pelada_id}): {type(data_ass)}")
                if isinstance(data_ass, list):
                    ranking_assistencias = data_ass
                elif isinstance(data_ass, dict):
                    ranking_assistencias = data_ass.get("ranking", data_ass.get("data", []))
                if ranking_assistencias and len(ranking_assistencias) > 0:
                    print(f"[DEBUG] First assistencia item: {ranking_assistencias[0]}")
            except Exception as e:
                print(f"[ERROR] Ranking assistencias: {e}")
                import traceback
                traceback.print_exc()
                ranking_assistencias = []
        
        return render_template(
            "peladas/perfil_publico.html",
            pelada=pelada,
            temporada_ativa=temporada_ativa,
            ranking_times=ranking_times,
            ranking_artilheiros=ranking_artilheiros,
            ranking_assistencias=ranking_assistencias
        )
    except ApiError as e:
        return render_template("errors/error.html", error="Pelada não encontrada"), 404
    except Exception as e:
        return render_template("errors/error.html", error="Erro ao carregar perfil público"), 500

@peladas_bp.route("/perfil/<nome_pelada>")
def perfil_publico_por_nome(nome_pelada: str):
    """Perfil público da pelada usando o nome (slug) - sem autenticação necessária"""
    from services import pelada_service, ranking_service
    from services.api_client import ApiError
    
    try:
        # Buscar pelada pelo nome (slug)
        pelada = buscar_pelada_por_nome(nome_pelada)
        
        if not pelada or not pelada.get("id"):
            return render_template("errors/error.html", error="Pelada não encontrada"), 404
        
        pelada_id = pelada["id"]
        
        # Buscar dados completos da pelada
        pelada_data = pelada_service.perfil_pelada(pelada_id)
        pelada = pelada_data.get("pelada", pelada)  # Usa dados completos se disponível
        temporada_ativa = pelada_data.get("temporada_ativa")
        
        # Buscar rankings se houver temporada ativa
        ranking_times = []
        ranking_artilheiros = []
        ranking_assistencias = []
        
        if temporada_ativa and temporada_ativa.get("id"):
            temporada_id = temporada_ativa["id"]
            
            # Ranking de times
            try:
                data_times = ranking_service.ranking_times(temporada_id)
                print(f"[DEBUG] Ranking times (nome '{nome_pelada}'): {type(data_times)}")
                if isinstance(data_times, list):
                    ranking_times = data_times
                elif isinstance(data_times, dict):
                    ranking_times = data_times.get("ranking", data_times.get("data", []))
                if ranking_times and len(ranking_times) > 0:
                    print(f"[DEBUG] First time item (nome): {ranking_times[0]}")
            except Exception as e:
                print(f"[ERROR] Ranking times (nome): {e}")
                import traceback
                traceback.print_exc()
                ranking_times = []
            
            # Ranking de artilheiros
            try:
                data_art = ranking_service.ranking_artilheiros(temporada_id, limit=10)
                print(f"[DEBUG] Ranking artilheiros (nome '{nome_pelada}'): {type(data_art)}")
                if isinstance(data_art, list):
                    ranking_artilheiros = data_art
                elif isinstance(data_art, dict):
                    ranking_artilheiros = data_art.get("ranking", data_art.get("data", []))
                if ranking_artilheiros and len(ranking_artilheiros) > 0:
                    print(f"[DEBUG] First artilheiro item (nome): {ranking_artilheiros[0]}")
            except Exception as e:
                print(f"[ERROR] Ranking artilheiros (nome): {e}")
                import traceback
                traceback.print_exc()
                ranking_artilheiros = []
            
            # Ranking de assistências
            try:
                data_ass = ranking_service.ranking_assistencias(temporada_id, limit=10)
                print(f"[DEBUG] Ranking assistencias (nome '{nome_pelada}'): {type(data_ass)}")
                if isinstance(data_ass, list):
                    ranking_assistencias = data_ass
                elif isinstance(data_ass, dict):
                    ranking_assistencias = data_ass.get("ranking", data_ass.get("data", []))
                if ranking_assistencias and len(ranking_assistencias) > 0:
                    print(f"[DEBUG] First assistencia item (nome): {ranking_assistencias[0]}")
            except Exception as e:
                print(f"[ERROR] Ranking assistencias (nome): {e}")
                import traceback
                traceback.print_exc()
                ranking_assistencias = []
        
        return render_template(
            "peladas/perfil_publico.html",
            pelada=pelada,
            temporada_ativa=temporada_ativa,
            ranking_times=ranking_times,
            ranking_artilheiros=ranking_artilheiros,
            ranking_assistencias=ranking_assistencias
        )
    except ApiError as e:
        return render_template("errors/error.html", error="Pelada não encontrada"), 404
    except Exception as e:
        return render_template("errors/error.html", error="Erro ao carregar perfil público"), 500

@peladas_bp.route("/peladas/<int:pelada_id>/edit", methods=["GET", "POST"])
def editar(pelada_id: int):
    if request.method == "POST":
        payload = {k:v for k,v in {
            "nome": request.form.get("nome","").strip() or None,
            "cidade": request.form.get("cidade","").strip() or None,
            "fuso_horario": request.form.get("fuso_horario","").strip() or None,
            "ativa": True if request.form.get("ativa") == "on" else False
        }.items() if v is not None}
        logo_file = request.files.get("logo")
        perfil_file = request.files.get("perfil")
        # Verificar se há arquivos válidos
        has_logo = logo_file and logo_file.filename and logo_file.filename.strip()
        has_perfil = perfil_file and perfil_file.filename and perfil_file.filename.strip()
        
        try:
            svc.atualizar_pelada(
                pelada_id, 
                payload,
                logo_file=logo_file if has_logo else None,
                perfil_file=perfil_file if has_perfil else None
            )
            flash("Pelada atualizada!", "ok")
            return redirect(url_for("peladas.perfil", pelada_id=pelada_id))
        except ApiError as e:
            flash(e.payload.get("erro","Erro ao atualizar"), "error")

    data = svc.perfil_pelada(pelada_id)
    return render_template("peladas/edit.html", **data)
