from services.api_client import api

def login(username: str, senha: str):
    return api("POST", "/api/usuarios/login", json={"username": username, "password": senha})

def register(email: str, senha: str, nome: str):
    return api("POST", "/api/usuarios/registrar", json={"username": nome, "email": email, "password": senha})

def me():
    return api("GET", "/api/usuarios/me")

def refresh(refresh_token: str):
    # se sua API exigir refresh via header Bearer, adapte aqui
    return api("POST", "/api/usuarios/refresh", json=None)
