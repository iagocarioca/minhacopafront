from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import jogador_service as svc
from services.api_client import ApiError

jogadores_bp = Blueprint("jogadores", __name__)

@jogadores_bp.route("/peladas/<int:pelada_id>/jogadores", methods=["GET", "POST"])
def list_create(pelada_id: int):
    if request.method == "POST":
        # Verifica se é uma requisição HTMX
        is_htmx = request.headers.get("HX-Request") == "true"
        
        try:
            foto_file = request.files.get("foto")
            svc.criar_jogador(
                pelada_id,
                request.form.get("nome_completo","").strip(),
                request.form.get("apelido","").strip() or None,
                request.form.get("telefone","").strip() or None,
                foto_file=foto_file if foto_file and foto_file.filename else None
            )
            if is_htmx:
                # Retorna apenas a lista de jogadores atualizada
                data = svc.listar_jogadores(pelada_id, page=1, per_page=50, ativo=None)
                return render_template("jogadores/_jogadores_list.html", data=data)
            flash("Jogador criado!", "ok")
        except ApiError as e:
            if is_htmx:
                # Retorna mensagem de erro para HTMX
                return f'<div class="rounded-md px-4 py-3 text-xs border backdrop-blur-xl bg-rose-50/60 border-rose-300/60 text-rose-800">{e.payload.get("erro","Erro ao criar jogador")}</div>', 400
            flash(e.payload.get("erro","Erro ao criar jogador"), "error")
        
        if is_htmx:
            return ""  # HTMX já retornou o conteúdo
        return redirect(url_for("jogadores.list_create", pelada_id=pelada_id))

    data = svc.listar_jogadores(pelada_id, page=int(request.args.get("page","1")), per_page=50, ativo=None)
    return render_template("jogadores/list.html", pelada_id=pelada_id, data=data)

@jogadores_bp.route("/jogadores/<int:jogador_id>/edit", methods=["GET","POST"])
def edit(jogador_id: int):
    if request.method == "POST":
        foto_file = request.files.get("foto")
        payload = {
            "nome_completo": request.form.get("nome_completo","").strip(),
            "apelido": request.form.get("apelido","").strip() or None,
            "telefone": request.form.get("telefone","").strip() or None,
            "ativo": True if request.form.get("ativo") == "on" else False
        }
        try:
            data = svc.atualizar_jogador(jogador_id, payload, foto_file=foto_file if foto_file and foto_file.filename else None)
            flash("Jogador atualizado!", "ok")
            pelada_id = data.get("jogador", {}).get("pelada_id")
            if pelada_id:
                return redirect(url_for("jogadores.list_create", pelada_id=pelada_id))
        except ApiError as e:
            flash(e.payload.get("erro","Erro ao atualizar"), "error")

    data = svc.obter_jogador(jogador_id)
    jogador = data.get("jogador", {})
    pelada_id = jogador.get("pelada_id")
    return render_template("jogadores/edit.html", jogador=jogador, pelada_id=pelada_id)
