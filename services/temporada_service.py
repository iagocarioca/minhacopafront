from services.api_client import api

def listar_temporadas(pelada_id: int, page=1, per_page=10):
    return api("GET", f"/api/peladas/{pelada_id}/temporadas", params={"page": page, "per_page": per_page})

def criar_temporada(pelada_id: int, inicio_mes: str, fim_mes: str):
    return api("POST", f"/api/peladas/{pelada_id}/temporadas", json={"inicio_mes": inicio_mes, "fim_mes": fim_mes})

def obter_temporada(temporada_id: int):
    return api("GET", f"/api/peladas/temporadas/{temporada_id}")

def encerrar_temporada(temporada_id: int):
    return api("POST", f"/api/peladas/temporadas/{temporada_id}/encerrar")
