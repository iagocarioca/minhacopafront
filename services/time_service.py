from services.api_client import api, api_upload

def listar_times_pelada(temporada_id: int, page: int = None, per_page: int = None):
    params = {}
    if page is not None:
        params["page"] = page
    if per_page is not None:
        params["per_page"] = per_page
    return api("GET", f"/api/peladas/temporadas/{temporada_id}/times", params=params if params else None)

def criar_time(temporada_id: int, nome: str, cor: str = None, escudo_file=None):
    if escudo_file and escudo_file.filename:
        # Upload com arquivo
        files = {"escudo": (escudo_file.filename, escudo_file, escudo_file.content_type)}
        data = {"nome": nome}
        if cor:
            data["cor"] = cor
        return api_upload("POST", f"/api/peladas/temporadas/{temporada_id}/times", files=files, data=data)
    else:
        # Sem arquivo, usa JSON normal
        payload = {"nome": nome}
        if cor:
            payload["cor"] = cor
        return api("POST", f"/api/peladas/temporadas/{temporada_id}/times", json=payload)

def obter_time(time_id: int):
    return api("GET", f"/api/peladas/times/{time_id}")

def adicionar_jogador(time_id: int, jogador_id: int, capitao: bool, posicao: str | int | None):
    payload = {"jogador_id": jogador_id, "capitao": bool(capitao), "posicao": posicao}
    return api("POST", f"/api/peladas/times/{time_id}/jogadores", json=payload)

def remover_jogador(time_id: int, jogador_id: int):
    return api("DELETE", f"/api/peladas/times/{time_id}/jogadores/{jogador_id}")

def atualizar_escudo(time_id: int, escudo_file):
    """Atualiza o escudo do time"""
    if escudo_file and escudo_file.filename:
        files = {"escudo": (escudo_file.filename, escudo_file, escudo_file.content_type)}
        return api_upload("PUT", f"/api/peladas/times/{time_id}", files=files, data={})
    else:
        raise ValueError("Arquivo de escudo é obrigatório")
