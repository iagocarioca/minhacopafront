from services.api_client import api, api_upload

def listar_jogadores(pelada_id: int, page=1, per_page=50, ativo=None):
    params = {"page": page, "per_page": per_page}
    if ativo is not None:
        params["ativo"] = "true" if ativo else "false"
    return api("GET", f"/api/peladas/{pelada_id}/jogadores", params=params)

def criar_jogador(pelada_id: int, nome_completo: str, apelido: str | None, telefone: str | None, foto_file=None):
    if foto_file and foto_file.filename:
        # Upload com arquivo
        files = {"foto": (foto_file.filename, foto_file, foto_file.content_type)}
        data = {
            "nome_completo": nome_completo,
            "apelido": apelido or "",
            "telefone": telefone or ""
        }
        return api_upload("POST", f"/api/peladas/{pelada_id}/jogadores", files=files, data=data)
    else:
        # Sem arquivo, usa JSON normal
        return api("POST", f"/api/peladas/{pelada_id}/jogadores", json={
            "nome_completo": nome_completo,
            "apelido": apelido or None,
            "telefone": telefone or None
        })

def obter_jogador(jogador_id: int):
    return api("GET", f"/api/peladas/jogadores/{jogador_id}")

def atualizar_jogador(jogador_id: int, payload: dict, foto_file=None):
    if foto_file and foto_file.filename:
        # Upload com arquivo
        files = {"foto": (foto_file.filename, foto_file, foto_file.content_type)}
        data = {}
        for key, value in payload.items():
            if isinstance(value, bool):
                data[key] = str(value).lower()
            else:
                data[key] = value or ""
        return api_upload("PUT", f"/api/peladas/jogadores/{jogador_id}", files=files, data=data)
    else:
        # Sem arquivo, usa JSON normal
        return api("PUT", f"/api/peladas/jogadores/{jogador_id}", json=payload)
