from services.api_client import api

def listar_partidas(rodada_id: int):
    return api("GET", f"/api/peladas/rodadas/{rodada_id}/partidas")

def criar_partida(rodada_id: int, time_casa_id: int, time_fora_id: int):
    return api("POST", f"/api/peladas/rodadas/{rodada_id}/partidas", json={"time_casa_id": time_casa_id, "time_fora_id": time_fora_id})

def obter_partida(partida_id: int):
    return api("GET", f"/api/peladas/partidas/{partida_id}")

def iniciar_partida(partida_id: int):
    return api("POST", f"/api/peladas/partidas/{partida_id}/iniciar")

def finalizar_partida(partida_id: int):
    return api("POST", f"/api/peladas/partidas/{partida_id}/finalizar")
