from services.api_client import api

def ranking_times(temporada_id: int):
    return api("GET", f"/api/peladas/temporadas/{temporada_id}/ranking/times")

def ranking_artilheiros(temporada_id: int, limit=10):
    return api("GET", f"/api/peladas/temporadas/{temporada_id}/ranking/artilheiros", params={"limit": limit})

def ranking_assistencias(temporada_id: int, limit=10):
    return api("GET", f"/api/peladas/temporadas/{temporada_id}/ranking/assistencias", params={"limit": limit})
