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
