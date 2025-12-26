from services.api_client import api

def criar_gol(partida_id: int, payload: dict):
    return api("POST", f"/api/peladas/partidas/{partida_id}/gols", json=payload)

def remover_gol(gol_id: int):
    return api("DELETE", f"/api/peladas/gols/{gol_id}")
