from services.api_client import api

def listar_rodadas(temporada_id: int, page=1, per_page=10):
    return api("GET", f"/api/peladas/temporadas/{temporada_id}/rodadas", params={"page": page, "per_page": per_page})

def criar_rodada(temporada_id: int, data_rodada: str, quantidade_times: int, jogadores_por_time: int, time_ids: list = None):
    payload = {
        "data_rodada": data_rodada,
        "quantidade_times": quantidade_times,
        "jogadores_por_time": jogadores_por_time
    }
    if time_ids:
        payload["time_ids"] = time_ids
    return api("POST", f"/api/peladas/temporadas/{temporada_id}/rodadas", json=payload)

def obter_rodada(rodada_id: int):
    return api("GET", f"/api/peladas/rodadas/{rodada_id}")

def listar_jogadores_rodada(rodada_id: int, posicao: int = None, apenas_ativos: bool = True):
    params = {}
    if posicao is not None:
        params["posicao"] = posicao
    if not apenas_ativos:
        params["apenas_ativos"] = "false"
    return api("GET", f"/api/peladas/rodadas/{rodada_id}/jogadores", params=params if params else None)
