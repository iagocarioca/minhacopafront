from flask import Flask, redirect, url_for, session, request, render_template, flash, Response
import requests
from services.api_client import API_BASE
from services.api_client import ApiError
from routes.auth import auth_bp
from routes.peladas import peladas_bp
from routes.jogadores import jogadores_bp
from routes.temporadas import temporadas_bp
from routes.rodadas import rodadas_bp
from routes.times import times_bp
from routes.partidas import partidas_bp
from routes.rankings import rankings_bp
from routes.votacoes import votacoes_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = "super-secret-key"  # troque em prod

    @app.get("/media/<path:subpath>")
    def media_proxy(subpath: str):
        """
        Proxy de imagens do backend (API_BASE) para o mesmo host do front.
        Isso permite capturar screenshots (html2canvas) sem bloquear imagens por CORS.
        Funciona sem autenticação para permitir acesso público.
        """
        # allowlist simples
        if not subpath.startswith("static/"):
            return ("Not found", 404)
        try:
            url = f"{API_BASE}/{subpath}"
            # Não envia token de autenticação para permitir acesso público
            r = requests.get(url, timeout=20)
            resp = Response(r.content, status=r.status_code)
            ct = r.headers.get("Content-Type") or "application/octet-stream"
            resp.headers["Content-Type"] = ct
            resp.headers["Cache-Control"] = "public, max-age=86400"
            return resp
        except Exception:
            return ("Not found", 404)
    
    # Filtro Jinja2 para criar slug do nome
    @app.template_filter('slug')
    def slug_filter(texto):
        import unicodedata
        import re
        if not texto:
            return ""
        # Remove acentos
        texto = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode('ascii')
        # Converte para minúsculas
        texto = texto.lower()
        # Remove caracteres especiais, mantém apenas letras, números e espaços
        texto = re.sub(r'[^a-z0-9\s-]', '', texto)
        # Substitui espaços por hífens
        texto = re.sub(r'\s+', '-', texto.strip())
        # Remove hífens múltiplos
        texto = re.sub(r'-+', '-', texto)
        return texto

    # Filtro Jinja2 para formatar datas no formato brasileiro (DD/MM/YYYY)
    @app.template_filter('data_br')
    def data_br_filter(data_str, incluir_hora=False):
        from datetime import datetime
        if not data_str:
            return ""
        try:
            # Tenta vários formatos comuns
            formatos = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%d/%m/%Y %H:%M:%S',
                '%d/%m/%Y %H:%M',
                '%d/%m/%Y',
            ]
            dt = None
            for fmt in formatos:
                try:
                    dt = datetime.strptime(str(data_str).strip(), fmt)
                    break
                except ValueError:
                    continue
            
            if not dt:
                return str(data_str)  # Retorna original se não conseguir parsear
            
            # Formata no padrão brasileiro
            if incluir_hora and (dt.hour != 0 or dt.minute != 0 or dt.second != 0):
                return dt.strftime('%d/%m/%Y %H:%M')
            else:
                return dt.strftime('%d/%m/%Y')
        except Exception:
            return str(data_str)  # Retorna original em caso de erro

    @app.before_request
    def _auth_guard():
        public_paths = {"/login", "/register"}
        public_prefixes = ["/peladas/", "/static/"]
        if request.path.startswith("/static/"):
            return None
        if request.path.startswith("/media/"):
            return None  # Permitir acesso público às imagens
        if request.path in public_paths:
            return None
        # Permitir acesso público ao perfil público da pelada (por ID ou nome)
        if request.path.startswith("/peladas/") and request.path.endswith("/publico"):
            return None
        if request.path.startswith("/perfil/"):
            return None
        # Permitir acesso público às rotas de votação
        if request.path.startswith("/votacoes/"):
            # Rotas públicas de votação: votar e resultado
            if "/votar" in request.path or "/resultado" in request.path:
                return None
        if request.path == "/":
            return redirect(url_for("peladas.list_create"))
        if not session.get("access_token"):
            return redirect(url_for("auth.login"))
        return None

    app.register_blueprint(auth_bp)
    app.register_blueprint(peladas_bp)
    app.register_blueprint(jogadores_bp)
    app.register_blueprint(temporadas_bp)
    app.register_blueprint(rodadas_bp)
    app.register_blueprint(times_bp)
    app.register_blueprint(partidas_bp)
    app.register_blueprint(rankings_bp)
    app.register_blueprint(votacoes_bp)

    # ----------------------------
    # Error handlers (UX)
    # - Nunca mostrar stacktrace em tela
    # - Para erros conhecidos (ApiError), mostrar toast e voltar
    # - Para 404/500, renderizar tela amigável
    # ----------------------------

    def _redirect_back_or_home():
        ref = request.headers.get("Referer")
        # evita loop (redirecionar pro mesmo URL repetidamente)
        if ref and ref != request.url:
            return redirect(ref)
        return redirect(url_for("peladas.list_create"))

    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        # 401/403: sessão expirada / token inválido -> força login (evita loop de redirects)
        if getattr(err, "status_code", None) in (401, 403):
            session.clear()
            flash("Sua sessão expirou. Faça login novamente.", "error")
            return redirect(url_for("auth.login"))

        msg = (err.payload or {}).get("erro") or str(err) or "Erro na API"
        flash(msg, "error")

        # Em GET, preferimos mostrar a tela amigável (evita redirect infinito para uma rota quebrada)
        if request.method == "GET":
            return render_template(
                "errors/error.html",
                code=getattr(err, "status_code", 400),
                title="Não foi possível concluir",
                message=msg,
            ), getattr(err, "status_code", 400)

        # Em POST/ações, volta para página anterior
        return _redirect_back_or_home()

    @app.errorhandler(404)
    def handle_404(_err):
        # Se não estiver autenticado, redireciona para login
        if not session.get("access_token"):
            return redirect(url_for("auth.login"))
        # toast + página amigável (para links quebrados)
        flash("Página não encontrada.", "error")
        return render_template(
            "errors/error.html",
            code=404,
            title="Página não encontrada",
            message="O link que você tentou acessar não existe ou foi movido.",
        ), 404

    @app.errorhandler(500)
    def handle_500(_err):
        # Se não estiver autenticado, redireciona para login
        if not session.get("access_token"):
            return redirect(url_for("auth.login"))
        flash("Erro interno. Tente novamente.", "error")
        return render_template(
            "errors/error.html",
            code=500,
            title="Erro interno",
            message="Ocorreu um erro inesperado. Tente novamente em alguns instantes.",
        ), 500

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        # Se não estiver autenticado, redireciona para login
        if not session.get("access_token"):
            return redirect(url_for("auth.login"))
        # fallback: evita página de erro crua
        flash("Ops! Algo deu errado. Tente novamente.", "error")
        # Em POST/PUT, melhor redirecionar de volta; em GET, renderiza página
        if request.method != "GET":
            return _redirect_back_or_home()
        return render_template(
            "errors/error.html",
            code=500,
            title="Erro inesperado",
            message="Ocorreu um erro inesperado. Tente novamente.",
        ), 500

    return app

app = create_app()

if __name__ == "__main__":
    # debug=False para não exibir stacktrace na tela (use FLASK_DEBUG no ambiente se precisar)
     app.run(host="0.0.0.0", port=5000, debug=True)
