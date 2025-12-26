from services.api_client import api, api_upload

def listar_peladas(page=1, per_page=10):
    return api("GET", "/api/peladas/", params={"page": page, "per_page": per_page})

def criar_pelada(nome: str, cidade: str, fuso_horario: str | None = None, logo_file=None, perfil_file=None):
    """Cria pelada com suporte a upload de imagens"""
    if logo_file or perfil_file:
        # Upload com FormData
        files = {}
        data = {"nome": nome, "cidade": cidade}
        if fuso_horario:
            data["fuso_horario"] = fuso_horario
        if logo_file:
            # Flask FileStorage precisa ser passado como tupla (nome, arquivo, content_type)
            files["logo"] = (logo_file.filename, logo_file, logo_file.content_type or 'image/jpeg')
        if perfil_file:
            files["perfil"] = (perfil_file.filename, perfil_file, perfil_file.content_type or 'image/jpeg')
        return api_upload("POST", "/api/peladas/", files=files, data=data)
    else:
        # Upload sem imagens (JSON)
        payload = {"nome": nome, "cidade": cidade}
        if fuso_horario:
            payload["fuso_horario"] = fuso_horario
        return api("POST", "/api/peladas/", json=payload)

def perfil_pelada(pelada_id: int):
    return api("GET", f"/api/peladas/{pelada_id}/perfil")

def atualizar_pelada(pelada_id: int, payload: dict, logo_file=None, perfil_file=None):
    """Atualiza pelada com suporte a upload de imagens"""
    if logo_file or perfil_file:
        # Upload com FormData
        files = {}
        data = {k: v for k, v in payload.items() if v is not None}
        # Converter boolean para string se necessário
        if "ativa" in data:
            data["ativa"] = str(data["ativa"]).lower()
        if logo_file:
            # Flask FileStorage precisa ser passado como tupla (nome, arquivo, content_type)
            files["logo"] = (logo_file.filename, logo_file, logo_file.content_type or 'image/jpeg')
        if perfil_file:
            files["perfil"] = (perfil_file.filename, perfil_file, perfil_file.content_type or 'image/jpeg')
        return api_upload("PUT", f"/api/peladas/{pelada_id}", files=files, data=data)
    else:
        # Atualização sem imagens (JSON)
        return api("PUT", f"/api/peladas/{pelada_id}", json=payload)
