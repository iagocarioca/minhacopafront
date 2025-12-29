from flask import Blueprint, render_template, request
from services import ranking_service as svc
from services.api_client import ApiError

rankings_bp = Blueprint("rankings", __name__)

@rankings_bp.route("/temporadas/<int:temporada_id>/ranking")
def hub(temporada_id: int):
    return render_template("rankings/hub.html", temporada_id=temporada_id)

@rankings_bp.route("/temporadas/<int:temporada_id>/ranking/times")
def times(temporada_id: int):
    try:
        data = svc.ranking_times(temporada_id)
        print(f"[DEBUG] Ranking times API response: {type(data)} - {data}")
        
        # Se a API retornar uma lista diretamente
        if isinstance(data, list):
            ranking = data
        # Se retornar um dicionário com a chave "ranking"
        elif isinstance(data, dict):
            ranking = data.get("ranking", [])
        else:
            ranking = []
        
        print(f"[DEBUG] Ranking times - total items: {len(ranking)}")
        return render_template("rankings/times.html", temporada_id=temporada_id, ranking=ranking)
    except ApiError as e:
        print(f"[ERROR API] Ranking times: {e.payload}")
        return render_template("rankings/times.html", temporada_id=temporada_id, ranking=[])
    except Exception as e:
        print(f"[ERROR] Ranking times: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return render_template("rankings/times.html", temporada_id=temporada_id, ranking=[])

@rankings_bp.route("/temporadas/<int:temporada_id>/ranking/artilheiros")
def artilheiros(temporada_id: int):
    limit = int(request.args.get("limit", "10"))
    try:
        data = svc.ranking_artilheiros(temporada_id, limit=limit)
        print(f"[DEBUG] Ranking artilheiros API response: {type(data)} - {data}")
        
        # Se a API retornar uma lista diretamente
        if isinstance(data, list):
            ranking = data
        # Se retornar um dicionário com a chave "ranking"
        elif isinstance(data, dict):
            ranking = data.get("ranking", [])
        else:
            ranking = []
        
        print(f"[DEBUG] Ranking artilheiros - total items: {len(ranking)}")
        return render_template("rankings/artilheiros.html", temporada_id=temporada_id, ranking=ranking, limit=limit)
    except ApiError as e:
        print(f"[ERROR API] Ranking artilheiros: {e.payload}")
        return render_template("rankings/artilheiros.html", temporada_id=temporada_id, ranking=[], limit=limit)
    except Exception as e:
        print(f"[ERROR] Ranking artilheiros: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return render_template("rankings/artilheiros.html", temporada_id=temporada_id, ranking=[], limit=limit)

@rankings_bp.route("/temporadas/<int:temporada_id>/ranking/assistencias")
def assistencias(temporada_id: int):
    limit = int(request.args.get("limit", "10"))
    try:
        data = svc.ranking_assistencias(temporada_id, limit=limit)
        print(f"[DEBUG] Ranking assistencias API response: {type(data)} - {data}")
        
        # Se a API retornar uma lista diretamente
        if isinstance(data, list):
            ranking = data
        # Se retornar um dicionário com a chave "ranking"
        elif isinstance(data, dict):
            ranking = data.get("ranking", [])
        else:
            ranking = []
        
        print(f"[DEBUG] Ranking assistencias - total items: {len(ranking)}")
        return render_template("rankings/assistencias.html", temporada_id=temporada_id, ranking=ranking, limit=limit)
    except ApiError as e:
        print(f"[ERROR API] Ranking assistencias: {e.payload}")
        return render_template("rankings/assistencias.html", temporada_id=temporada_id, ranking=[], limit=limit)
    except Exception as e:
        print(f"[ERROR] Ranking assistencias: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return render_template("rankings/assistencias.html", temporada_id=temporada_id, ranking=[], limit=limit)

@rankings_bp.route("/temporadas/<int:temporada_id>/scout")
def scout(temporada_id: int):
    """Exibe o scout anual da temporada com estatísticas e campeões"""
    from services import temporada_service as temp_svc
    from services import time_service as time_svc
    
    try:
        # Busca informações da temporada
        temporada_data = temp_svc.obter_temporada(temporada_id)
        temporada = temporada_data.get("temporada", {}) if isinstance(temporada_data, dict) else {}
        
        # Busca ranking de times para encontrar o campeão
        ranking_times_data = svc.ranking_times(temporada_id)
        if isinstance(ranking_times_data, list):
            ranking_times = ranking_times_data
        elif isinstance(ranking_times_data, dict):
            ranking_times = ranking_times_data.get("ranking", [])
        else:
            ranking_times = []
        
        time_campeao = None
        jogadores_campeoes = []
        if ranking_times and len(ranking_times) > 0:
            primeiro_lugar = ranking_times[0]
            time_campeao = primeiro_lugar.get("time", {}) if isinstance(primeiro_lugar, dict) else primeiro_lugar
            
            # Busca jogadores do time campeão
            if time_campeao and time_campeao.get("id"):
                try:
                    time_data = time_svc.obter_time(time_campeao["id"])
                    if isinstance(time_data, dict):
                        time_full = time_data.get("time", time_data)
                        jogadores_campeoes = time_full.get("jogadores", []) if isinstance(time_full, dict) else []
                except Exception as e:
                    print(f"[WARN] Erro ao buscar jogadores do time campeão: {e}")
                    jogadores_campeoes = []
        
        # Busca ranking de artilheiros para calcular total de gols
        artilheiros_data = svc.ranking_artilheiros(temporada_id, limit=1000)  # Limite alto para pegar todos
        if isinstance(artilheiros_data, list):
            ranking_artilheiros = artilheiros_data
        elif isinstance(artilheiros_data, dict):
            ranking_artilheiros = artilheiros_data.get("ranking", [])
        else:
            ranking_artilheiros = []
        
        total_gols = 0
        for item in ranking_artilheiros:
            if isinstance(item, dict):
                # Tenta diferentes campos possíveis (mesma lógica do template)
                jogador = item.get("jogador", {})
                gols = (jogador.get("total_gols") if isinstance(jogador, dict) else None) or item.get("gols") or item.get("total_gols") or 0
                total_gols += int(gols) if gols else 0
            elif isinstance(item, (int, float)):
                total_gols += int(item)
        
        # Busca ranking de assistências para calcular total
        assistencias_data = svc.ranking_assistencias(temporada_id, limit=1000)  # Limite alto para pegar todos
        if isinstance(assistencias_data, list):
            ranking_assistencias = assistencias_data
        elif isinstance(assistencias_data, dict):
            ranking_assistencias = assistencias_data.get("ranking", [])
        else:
            ranking_assistencias = []
        
        total_assistencias = 0
        for item in ranking_assistencias:
            if isinstance(item, dict):
                # Tenta diferentes campos possíveis (mesma lógica do template)
                jogador = item.get("jogador", {})
                assistencias = (jogador.get("total_assistencias") if isinstance(jogador, dict) else None) or item.get("assistencias") or item.get("total_assistencias") or 0
                total_assistencias += int(assistencias) if assistencias else 0
            elif isinstance(item, (int, float)):
                total_assistencias += int(item)
        
        return render_template(
            "rankings/scout.html",
            temporada_id=temporada_id,
            temporada=temporada,
            time_campeao=time_campeao,
            jogadores_campeoes=jogadores_campeoes,
            total_gols=total_gols,
            total_assistencias=total_assistencias
        )
    except Exception as e:
        print(f"[ERROR] Scout: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return render_template(
            "rankings/scout.html",
            temporada_id=temporada_id,
            temporada={},
            time_campeao=None,
            jogadores_campeoes=[],
            total_gols=0,
            total_assistencias=0
        )