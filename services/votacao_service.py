from services.api_client import api

def criar_votacao(rodada_id: int, abre_em: str, fecha_em: str, tipo: str):
    return api("POST", f"/api/peladas/rodadas/{rodada_id}/votacoes", json={
        "abre_em": abre_em,
        "fecha_em": fecha_em,
        "tipo": tipo
    })

def obter_votacao(votacao_id: int):
    """Busca detalhes de uma votação (se a API implementar GET)"""
    try:
        return api("GET", f"/api/peladas/votacoes/{votacao_id}")
    except Exception:
        return None

def obter_resultado(votacao_id: int):
    """Busca o resultado/ranking de uma votação específica"""
    return api("GET", f"/api/peladas/votacoes/{votacao_id}/resultado")

def obter_resultados_rodada(rodada_id: int, tipo: str = None):
    """Busca resultados de todas as votações de uma rodada"""
    params = {"tipo": tipo} if tipo else None
    return api("GET", f"/api/peladas/rodadas/{rodada_id}/votacoes/resultados", params=params)

def votar(votacao_id: int, jogador_votante_id: int, jogador_votado_id: int, pontos: int):
    return api("POST", f"/api/peladas/votacoes/{votacao_id}/votar", json={
        "jogador_votante_id": jogador_votante_id,
        "jogador_votado_id": jogador_votado_id,
        "pontos": pontos
    })
