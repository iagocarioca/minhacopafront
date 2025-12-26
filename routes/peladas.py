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
