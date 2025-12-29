import requests
from flask import session

API_BASE = "http://192.168.18.162:5001"

class ApiError(Exception):
    def __init__(self, status_code: int, payload: dict | None = None):
        super().__init__(payload.get("erro") if isinstance(payload, dict) and payload.get("erro") else f"API error {status_code}")
        self.status_code = status_code
        self.payload = payload or {}

def api(method: str, path: str, json=None, params=None):
    headers = {"Content-Type": "application/json"}
    token = session.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = API_BASE + path
    print(f"[API] {method} {url} params={params}")  # DEBUG
    r = requests.request(method, url, json=json, params=params, headers=headers, timeout=20)
    print(f"[API] Status: {r.status_code}")  # DEBUG

    try:
        data = r.json() if r.text else {}
    except Exception as e:
        print(f"[API] Error parsing JSON: {e}, text: {r.text[:200]}")  # DEBUG
        data = {"erro": "Resposta inválida da API", "raw": r.text}

    if r.status_code >= 400:
        print(f"[API] Error response: {data}")  # DEBUG
        raise ApiError(r.status_code, data if isinstance(data, dict) else {"erro": "Erro", "data": data})
    return data

def api_upload(method: str, path: str, files=None, data=None, params=None):
    """API call for file uploads (FormData)"""
    headers = {}
    token = session.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    # NÃO definir Content-Type - o requests define automaticamente com boundary para multipart/form-data

    url = API_BASE + path
    print(f"[API] {method} {url} (upload) files={list(files.keys()) if files else None} data={data}")  # DEBUG
    r = requests.request(method, url, files=files, data=data, params=params, headers=headers, timeout=30)
    print(f"[API] Status: {r.status_code}")  # DEBUG
    print(f"[API] Request Content-Type: {r.request.headers.get('Content-Type', 'N/A')}")  # DEBUG

    try:
        response_data = r.json() if r.text else {}
    except Exception as e:
        print(f"[API] Error parsing JSON: {e}, text: {r.text[:200]}")  # DEBUG
        response_data = {"erro": "Resposta inválida da API", "raw": r.text}

    if r.status_code >= 400:
        print(f"[API] Error response: {response_data}")  # DEBUG
        raise ApiError(r.status_code, response_data if isinstance(response_data, dict) else {"erro": "Erro", "data": response_data})
    return response_data
