# PRD - Product Requirements Document
## Sistema de Gestão de Peladas (Pelada Manager)

### 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Autenticação](#autenticação)
4. [Estrutura de Dados](#estrutura-de-dados)
5. [Rotas e Endpoints](#rotas-e-endpoints)
6. [APIs Consumidas](#apis-consumidas)
7. [Fluxos Principais](#fluxos-principais)
8. [Funcionalidades Especiais](#funcionalidades-especiais)
9. [Upload de Arquivos](#upload-de-arquivos)
10. [Navegação Hierárquica](#navegação-hierárquica)
11. [Tecnologias Utilizadas](#tecnologias-utilizadas)

---

## Visão Geral

Sistema web para gestão de peladas (peladas de futebol), permitindo:
- Gerenciamento de peladas, temporadas, rodadas e partidas
- Cadastro de jogadores e times
- Registro de gols e assistências
- Sistema de votações (MVP, jogador/goleiro da noite)
- Rankings e estatísticas
- Perfis públicos de peladas

**Base URL da API**: `http://192.168.18.162:5001` (configurável em `services/api_client.py`)

---

## Arquitetura

### Estrutura de Pastas
```
jinga/
├── app.py                 # Aplicação Flask principal
├── routes/               # Blueprints de rotas
│   ├── auth.py
│   ├── peladas.py
│   ├── jogadores.py
│   ├── temporadas.py
│   ├── rodadas.py
│   ├── times.py
│   ├── partidas.py
│   ├── rankings.py
│   └── votacoes.py
├── services/             # Camada de serviços (API clients)
│   ├── api_client.py    # Cliente HTTP base
│   ├── auth_service.py
│   ├── pelada_service.py
│   ├── jogador_service.py
│   ├── temporada_service.py
│   ├── rodada_service.py
│   ├── time_service.py
│   ├── partida_service.py
│   ├── gol_service.py
│   ├── ranking_service.py
│   └── votacao_service.py
└── templates/           # Templates Jinja2
```

### Padrão de Arquitetura
- **MVC**: Routes (Controllers) → Services (Models) → Templates (Views)
- **Separação de Responsabilidades**: 
  - Routes: Validação de entrada, renderização de templates, redirecionamentos
  - Services: Comunicação com API, transformação de dados
  - Templates: Apresentação visual

---

## Autenticação

### Fluxo de Autenticação

1. **Login** (`POST /login`)
   - **Formulário HTML recebe**: `username`, `senha`
   - **API recebe (JSON)**: `{"username": username, "password": senha}`
   - **API retorna**: `{"token_acesso": "...", "token_atualizacao": "..."}`
   - Armazena tokens na sessão Flask (`session["access_token"]`)

2. **Registro** (`POST /register`)
   - **Formulário HTML recebe**: `email`, `senha`, `nome`
   - **API recebe (JSON)**: `{"username": nome, "email": email, "password": senha}`
   - **Nota**: O campo `username` na API é preenchido com o `nome` do formulário

3. **Logout** (`GET /logout`)
   - Limpa sessão

### Proteção de Rotas

Middleware `@app.before_request` em `app.py`:
- Rotas públicas: `/login`, `/register`, `/peladas/*/publico`, `/perfil/*`, `/votacoes/*/votar`, `/votacoes/*/resultado`
- Todas as outras rotas exigem `session.get("access_token")`
- Se não autenticado → redireciona para `/login`

### Headers de Autenticação

Todas as requisições à API incluem:
```http
Authorization: Bearer {access_token}
```

---

## Estrutura de Dados

### Hierarquia de Entidades

```
Pelada
  ├── Jogadores (muitos)
  ├── Temporadas (muitos)
      ├── Times (muitos)
      │   └── TimeJogadores (muitos) [relação jogador-time]
      ├── Rodadas (muitos)
      │   ├── Partidas (muitos)
      │   │   └── Gols (muitos)
      │   └── Votações (muitos)
      │       └── Votos (muitos)
      └── Rankings
          ├── Ranking Times
          ├── Ranking Artilheiros
          └── Ranking Assistencias
```

### Modelos de Dados Principais

#### Pelada
```json
{
  "id": 1,
  "nome": "Pelada do Bairro",
  "cidade": "São Paulo",
  "fuso_horario": "America/Sao_Paulo",
  "ativa": true,
  "logo_url": "/static/peladas/1/logo.jpg",
  "perfil_url": "/static/peladas/1/perfil.jpg"
}
```

#### Jogador
```json
{
  "id": 1,
  "pelada_id": 1,
  "nome_completo": "João Silva",
  "apelido": "João",
  "telefone": "+5511999999999",
  "ativo": true,
  "foto_url": "/static/jogadores/1/foto.jpg"
}
```

#### Temporada
```json
{
  "id": 1,
  "pelada_id": 1,
  "inicio_mes": "2024-01-01",
  "fim_mes": "2024-12-31",
  "ativa": true
}
```

#### Rodada
```json
{
  "id": 1,
  "temporada_id": 1,
  "data_rodada": "2024-01-15",
  "quantidade_times": 4,
  "jogadores_por_time": 10,
  "status": "em_andamento",
  "times": [...]
}
```

#### Time
```json
{
  "id": 1,
  "temporada_id": 1,
  "nome": "Time Azul",
  "cor": "Azul",
  "escudo_url": "/static/times/1/escudo.jpg",
  "jogadores": [
    {
      "id": 1,
      "jogador": {...},
      "capitao": true,
      "posicao": "Goleiro"
    }
  ]
}
```

#### Partida
```json
{
  "id": 1,
  "rodada_id": 1,
  "time_casa_id": 1,
  "time_fora_id": 2,
  "gols_casa": 3,
  "gols_fora": 1,
  "status": "finalizada",
  "time_casa": {...},
  "time_fora": {...},
  "gols": [...]
}
```

#### Gol
```json
{
  "id": 1,
  "partida_id": 1,
  "time_id": 1,
  "jogador_id": 5,
  "assistencia_id": 6,
  "minuto": 25,
  "gol_contra": false
}
```

#### Votação
```json
{
  "id": 1,
  "rodada_id": 1,
  "tipo": "MVP",
  "abre_em": "2024-01-15 20:00:00",
  "fecha_em": "2024-01-15 23:59:59",
  "status": "aberta"
}
```

#### Voto
```json
{
  "id": 1,
  "votacao_id": 1,
  "jogador_votante_id": 1,
  "jogador_votado_id": 5,
  "pontos": 1
}
```

---

## Rotas e Endpoints

### Autenticação (`routes/auth.py`)

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|--------------|
| GET/POST | `/login` | Login de usuário | Pública |
| GET/POST | `/register` | Registro de usuário | Pública |
| GET | `/logout` | Logout | Requerida |

### Peladas (`routes/peladas.py`)

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|--------------|
| GET/POST | `/peladas` | Lista/cria peladas | Requerida |
| GET | `/peladas/<id>` | Perfil da pelada | Requerida |
| GET | `/peladas/<id>/publico` | Perfil público (por ID) | Pública |
| GET | `/perfil/<nome_slug>` | Perfil público (por nome) | Pública |
| GET | `/peladas/<id>/scout-anual` | Scout anual consolidado | Requerida |
| GET/POST | `/peladas/<id>/edit` | Edita pelada | Requerida |

### Jogadores (`routes/jogadores.py`)

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|--------------|
| GET/POST | `/peladas/<pelada_id>/jogadores` | Lista/cria jogadores | Requerida |
| GET/POST | `/jogadores/<id>/edit` | Edita jogador | Requerida |

### Temporadas (`routes/temporadas.py`)

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|--------------|
| GET/POST | `/peladas/<pelada_id>/temporadas` | Lista/cria temporadas | Requerida |
| GET/POST | `/temporadas/<id>` | Detalhe/encerra temporada | Requerida |

### Rodadas (`routes/rodadas.py`)

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|--------------|
| GET/POST | `/temporadas/<temporada_id>/rodadas` | Lista/cria rodadas | Requerida |
| GET/POST | `/rodadas/<id>` | Detalhe da rodada (inclui partidas) | Requerida |

**Nota**: A rota `/rodadas/<id>/partidas` foi removida. As partidas agora são exibidas diretamente na página de detalhes da rodada.

### Times (`routes/times.py`)

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|--------------|
| GET/POST | `/temporadas/<temporada_id>/times` | Lista/cria times | Requerida |
| GET/POST | `/times/<id>` | Detalhe do time (gerencia jogadores) | Requerida |

**Ações no detalhe do time**:
- `action=add`: Adiciona jogador ao time
- `action=remove`: Remove jogador do time
- `action=update`: Atualiza posição do jogador
- `action=update_escudo`: Atualiza escudo do time

### Partidas (`routes/partidas.py`)

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|--------------|
| GET | `/partidas/<id>` | Detalhe da partida | Requerida |
| POST | `/partidas/<id>/iniciar` | Inicia partida | Requerida |
| POST | `/partidas/<id>/finalizar` | Finaliza partida | Requerida |
| POST | `/partidas/<id>/gol` | Cria gol (HTMX) | Requerida |
| POST | `/gols/<id>/delete` | Remove gol (HTMX) | Requerida |

**Nota**: A criação de partidas foi movida para `/rodadas/<id>` (POST).

### Rankings (`routes/rankings.py`)

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|--------------|
| GET | `/temporadas/<temporada_id>/ranking` | Hub de rankings | Requerida |
| GET | `/temporadas/<temporada_id>/ranking/times` | Ranking de times | Requerida |
| GET | `/temporadas/<temporada_id>/ranking/artilheiros` | Ranking de artilheiros | Requerida |
| GET | `/temporadas/<temporada_id>/ranking/assistencias` | Ranking de assistências | Requerida |
| GET | `/temporadas/<temporada_id>/scout` | Scout da temporada | Requerida |

### Votações (`routes/votacoes.py`)

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|--------------|
| GET/POST | `/rodadas/<rodada_id>/votacoes` | Cria votação | Requerida |
| GET/POST | `/votacoes/<id>/votar` | Vota (público) | Pública |
| GET | `/votacoes/<id>/resultado` | Resultado da votação | Pública |
| GET | `/rodadas/<rodada_id>/votacoes/resultados` | Resultados de todas as votações | Requerida |
| POST | `/votacoes/<id>/encerrar` | Encerra votação | Requerida |
| POST | `/votacoes/<id>/gerar-imagem` | Gera imagem do vencedor | Requerida |

---

## APIs Consumidas

### Base URL
```
http://192.168.18.162:5001
```

### Cliente HTTP (`services/api_client.py`)

**Função `api(method, path, json=None, params=None)`**:
- Métodos: GET, POST, PUT, DELETE
- Headers: `Authorization: Bearer {token}` (se disponível na sessão)
- Content-Type: `application/json`
- Timeout: 20 segundos
- Tratamento de erros: Lança `ApiError` para status >= 400

**Função `api_upload(method, path, files=None, data=None, params=None)`**:
- Para uploads multipart/form-data
- Não define Content-Type (deixa requests definir com boundary)
- Timeout: 30 segundos

### Endpoints da API

#### Autenticação (`/api/usuarios/`)
- `POST /api/usuarios/login` - Login
  - **Payload**: `{"username": string, "password": string}`
  - **Resposta**: `{"token_acesso": string, "token_atualizacao": string}`
- `POST /api/usuarios/registrar` - Registro
  - **Payload**: `{"username": string, "email": string, "password": string}`
  - **Nota**: `username` é o nome do usuário (não email)
- `GET /api/usuarios/me` - Dados do usuário logado
- `POST /api/usuarios/refresh` - Refresh token

#### Peladas (`/api/peladas/`)
- `GET /api/peladas/` - Lista peladas (paginação)
  - **Query params**: `page`, `per_page`
- `POST /api/peladas/` - Cria pelada
  - **Com arquivos (multipart/form-data)**: `{"nome": string, "cidade": string, "fuso_horario": string?}`, files: `logo`, `perfil`
  - **Sem arquivos (JSON)**: `{"nome": string, "cidade": string, "fuso_horario": string?}`
- `GET /api/peladas/{id}/perfil` - Perfil da pelada
- `PUT /api/peladas/{id}` - Atualiza pelada
  - **Com arquivos (multipart/form-data)**: `{"nome": string?, "cidade": string?, "fuso_horario": string?, "ativa": boolean?}`, files: `logo?`, `perfil?`
  - **Sem arquivos (JSON)**: `{"nome": string?, "cidade": string?, "fuso_horario": string?, "ativa": boolean?}`

#### Jogadores (`/api/peladas/{pelada_id}/jogadores`)
- `GET /api/peladas/{pelada_id}/jogadores` - Lista jogadores
  - **Query params**: `page`, `per_page`, `ativo` (true/false)
- `POST /api/peladas/{pelada_id}/jogadores` - Cria jogador
  - **Com arquivo (multipart/form-data)**: `{"nome_completo": string, "apelido": string?, "telefone": string?}`, file: `foto`
  - **Sem arquivo (JSON)**: `{"nome_completo": string, "apelido": string?, "telefone": string?}`
- `GET /api/peladas/jogadores/{id}` - Obtém jogador
- `PUT /api/peladas/jogadores/{id}` - Atualiza jogador
  - **Com arquivo (multipart/form-data)**: `{"nome_completo": string, "apelido": string?, "telefone": string?, "ativo": boolean}`, file: `foto?`
  - **Sem arquivo (JSON)**: `{"nome_completo": string, "apelido": string?, "telefone": string?, "ativo": boolean}`

#### Temporadas (`/api/peladas/{pelada_id}/temporadas`)
- `GET /api/peladas/{pelada_id}/temporadas` - Lista temporadas
  - **Query params**: `page`, `per_page`
- `POST /api/peladas/{pelada_id}/temporadas` - Cria temporada
  - **Payload**: `{"inicio_mes": string (YYYY-MM-DD), "fim_mes": string (YYYY-MM-DD)}`
- `GET /api/peladas/temporadas/{id}` - Obtém temporada
- `POST /api/peladas/temporadas/{id}/encerrar` - Encerra temporada

#### Rodadas (`/api/peladas/temporadas/{temporada_id}/rodadas`)
- `GET /api/peladas/temporadas/{temporada_id}/rodadas` - Lista rodadas
  - **Query params**: `page`, `per_page`
- `POST /api/peladas/temporadas/{temporada_id}/rodadas` - Cria rodada
  - **Payload**: `{"data_rodada": string (YYYY-MM-DD), "quantidade_times": int, "jogadores_por_time": int, "time_ids": int[]?}`
- `GET /api/peladas/rodadas/{id}` - Obtém rodada
- `GET /api/peladas/rodadas/{id}/jogadores` - Lista jogadores da rodada
  - **Query params**: `posicao` (int?), `apenas_ativos` (true/false, default: true)

#### Times (`/api/peladas/temporadas/{temporada_id}/times`)
- `GET /api/peladas/temporadas/{temporada_id}/times` - Lista times
  - **Query params**: `page?`, `per_page?`
- `POST /api/peladas/temporadas/{temporada_id}/times` - Cria time
  - **Com arquivo (multipart/form-data)**: `{"nome": string, "cor": string?}`, file: `escudo`
  - **Sem arquivo (JSON)**: `{"nome": string, "cor": string?}`
- `GET /api/peladas/times/{id}` - Obtém time
- `PUT /api/peladas/times/{id}` - Atualiza escudo do time
  - **Payload (multipart/form-data)**: file: `escudo` (obrigatório)
- `POST /api/peladas/times/{id}/jogadores` - Adiciona jogador ao time
  - **Payload**: `{"jogador_id": int, "capitao": boolean, "posicao": string|int?}`
- `DELETE /api/peladas/times/{id}/jogadores/{jogador_id}` - Remove jogador do time

#### Partidas (`/api/peladas/rodadas/{rodada_id}/partidas`)
- `GET /api/peladas/rodadas/{rodada_id}/partidas` - Lista partidas
- `POST /api/peladas/rodadas/{rodada_id}/partidas` - Cria partida
  - **Payload**: `{"time_casa_id": int, "time_fora_id": int}`
- `GET /api/peladas/partidas/{id}` - Obtém partida
- `POST /api/peladas/partidas/{id}/iniciar` - Inicia partida
- `POST /api/peladas/partidas/{id}/finalizar` - Finaliza partida

#### Gols (`/api/peladas/partidas/{partida_id}/gols`)
- `POST /api/peladas/partidas/{partida_id}/gols` - Cria gol
  - **Payload**: `{"time_id": int, "jogador_id": int, "minuto": int?, "gol_contra": boolean, "assistencia_id": int?}`
- `DELETE /api/peladas/gols/{id}` - Remove gol

#### Rankings (`/api/peladas/temporadas/{temporada_id}/ranking/`)
- `GET /api/peladas/temporadas/{temporada_id}/ranking/times` - Ranking de times
- `GET /api/peladas/temporadas/{temporada_id}/ranking/artilheiros` - Ranking de artilheiros
  - **Query params**: `limit` (int, default: 10)
- `GET /api/peladas/temporadas/{temporada_id}/ranking/assistencias` - Ranking de assistências
  - **Query params**: `limit` (int, default: 10)

#### Votações (`/api/peladas/rodadas/{rodada_id}/votacoes`)
- `GET /api/peladas/rodadas/{rodada_id}/votacoes` - Lista votações (opcional, pode não existir)
- `POST /api/peladas/rodadas/{rodada_id}/votacoes` - Cria votação
  - **Payload**: `{"abre_em": string (datetime), "fecha_em": string (datetime), "tipo": string}`
- `GET /api/peladas/votacoes/{id}` - Obtém votação (opcional, pode não existir)
- `GET /api/peladas/votacoes/{id}/resultado` - Resultado da votação
- `GET /api/peladas/rodadas/{rodada_id}/votacoes/resultados` - Resultados de todas as votações
  - **Query params**: `tipo` (string?)
- `POST /api/peladas/votacoes/{id}/votar` - Registra voto
  - **Payload**: `{"jogador_votante_id": int, "jogador_votado_id": int, "pontos": int}`
- `POST /api/peladas/votacoes/{id}/encerrar` - Encerra votação

---

## Fluxos Principais

### 1. Fluxo de Criação de Partida

1. Usuário acessa `/temporadas/<id>/rodadas`
2. Cria rodada com data, quantidade de times, jogadores por time
3. Seleciona times que participarão
4. Acessa `/rodadas/<id>` (detalhe da rodada)
5. Visualiza lista de partidas (se houver)
6. Clica em "Criar Partida"
7. Seleciona time casa e time fora
8. Partida é criada e aparece na lista

### 2. Fluxo de Registro de Gols

1. Usuário acessa `/partidas/<id>`
2. Partida deve estar "em_andamento"
3. Clica em "Registrar Gol"
4. Seleciona time, jogador, minuto (opcional), assistência (opcional)
5. Marca "Gol contra" se necessário
6. Gol é registrado via HTMX (atualiza placar e timeline sem reload)

### 3. Fluxo de Votação

1. Usuário acessa `/rodadas/<id>/votacoes`
2. Cria votação com tipo (MVP, Jogador da Noite, etc), data de abertura e fechamento
3. Compartilha link público: `/votacoes/<id>/votar?rodada_id=<id>`
4. Jogadores acessam link público
5. Informam nome (busca flexível por apelido/nome completo)
6. Selecionam até 3 jogadores (agrupados por posição)
7. Voto é registrado
8. Após fechamento, visualiza resultado em `/votacoes/<id>/resultado`

### 4. Fluxo de Escalação de Times

1. Usuário acessa `/temporadas/<id>/times`
2. Cria times para a temporada
3. Acessa `/times/<id>` (detalhe do time)
4. Visualiza jogadores disponíveis (exclui os já em outros times)
5. Adiciona jogadores ao time (com posição e capitão)
6. Pode remover ou atualizar posição de jogadores

### 5. Fluxo de Rankings

1. Usuário acessa `/temporadas/<id>/ranking`
2. Escolhe tipo de ranking:
   - Times (pontos, saldo de gols)
   - Artilheiros (total de gols)
   - Assistencias (total de assistências)
3. Pode compartilhar ranking (gera screenshot)

---

## Funcionalidades Especiais

### 1. HTMX (Interações Dinâmicas)

**Onde é usado**:
- Adicionar/remover jogadores de times (sem reload)
- Criar jogadores (atualiza lista sem reload)
- Registrar gols (atualiza placar e timeline sem reload)
- Remover gols (atualiza placar e timeline sem reload)

**Exemplo (Registrar Gol)**:
```html
<form hx-post="/partidas/{{partida.id}}/gol" 
      hx-target="#placar-timeline" 
      hx-swap="innerHTML">
  <!-- campos do formulário -->
</form>
```

### 2. Compartilhamento de Rankings

**Função JavaScript**: `window.shareScreenshot(containerId, filename, titleText)`

**Funcionalidade**:
- Captura screenshot de um container HTML usando `html2canvas`
- Esconde elementos com `data-share-hide="1"` durante captura
- Se suportar Web Share API (Android/WhatsApp), compartilha imagem
- Senão, mostra prévia e permite download

**Uso**:
```javascript
shareScreenshot('ranking-container', 'ranking.png', 'Ranking de Artilheiros');
```

### 3. Navegação Hierárquica

**Função JavaScript**: `smartBack()`

**Lógica**:
- Não usa histórico do navegador
- Navega seguindo hierarquia da aplicação:
  - Detalhe de partida → Detalhe da rodada
  - Detalhe da rodada → Lista de rodadas
  - Lista de rodadas → Detalhe da temporada
  - Detalhe da temporada → Lista de temporadas
  - Lista de temporadas → Perfil da pelada
  - Perfil da pelada → Lista de peladas

**Atributos HTML usados**:
- `data-rodada-id`: ID da rodada (em páginas de partida)
- `data-temporada-id`: ID da temporada (em páginas de rodada)
- `data-pelada-id`: ID da pelada (em páginas de temporada/jogador)

### 4. Busca Flexível de Jogadores

**Função**: `_buscar_jogador_por_nome(rodada_id, nome_busca)`

**Lógica**:
1. Match exato (case-insensitive) por apelido ou nome completo
2. Match parcial (contém) por apelido ou nome completo
3. Match parcial invertido (nome_busca contém parte do nome)

**Uso**: Votação pública (jogador informa nome para votar)

### 5. Agrupamento de Jogadores por Posição

**Função**: `_collect_jogadores_por_posicao(rodada_id)`

**Lógica**:
- Busca todos os jogadores da rodada via API
- Agrupa por posição (Goleiro, Zagueiro, Lateral, Meia, Atacante, etc)
- Ordena posições em ordem lógica (Goleiro primeiro, depois defesa, meio, ataque)
- Ordena jogadores dentro de cada posição alfabeticamente

**Uso**: Formulário de votação (jogadores agrupados por posição)

### 6. Enriquecimento de Dados

**Padrão comum**: Enriquecer objetos com dados relacionados

**Exemplo (Partidas na Rodada)**:
```python
# Busca partidas
partidas = partida_svc.listar_partidas(rodada_id)

# Busca times disponíveis
times_disponiveis = time_svc.listar_times_pelada(temporada_id)

# Cria mapa de times
times_map = {t["id"]: t for t in times_disponiveis}

# Enriquece partidas com dados completos dos times
for p in partidas:
    casa_id = p.get("time_casa_id")
    fora_id = p.get("time_fora_id")
    if casa_id in times_map:
        p["time_casa_full"] = times_map[casa_id]
    if fora_id in times_map:
        p["time_fora_full"] = times_map[fora_id]
```

### 7. Geração de Imagem do Vencedor

**Rota**: `POST /votacoes/<id>/gerar-imagem`

**Funcionalidade**:
- Busca resultado da votação
- Filtra por tipo (jogador ou goleiro)
- Seleciona mais votado
- Baixa foto do jogador
- Envia para webhook n8n com prompt de edição
- Retorna imagem editada (estilo neon)

**Webhook n8n**: `https://xai.aurora5.com/v1/gemini-edit-image`

---

## Upload de Arquivos

### Tipos de Upload

1. **Logo da Pelada** (`logo`)
2. **Perfil da Pelada** (`perfil`)
3. **Foto do Jogador** (`foto`)
4. **Escudo do Time** (`escudo`)

### Formato de Upload

**Content-Type**: `multipart/form-data`

**Exemplo (Criar Pelada)**:
```python
files = {
    "logo": (logo_file.filename, logo_file, logo_file.content_type),
    "perfil": (perfil_file.filename, perfil_file, perfil_file.content_type)
}
data = {
    "nome": "Pelada do Bairro",
    "cidade": "São Paulo",
    "fuso_horario": "America/Sao_Paulo"
}
api_upload("POST", "/api/peladas/", files=files, data=data)
```

### Proxy de Imagens

**Rota**: `GET /media/<path:subpath>`

**Funcionalidade**:
- Proxy de imagens do backend para o mesmo host do frontend
- Permite captura de screenshots sem problemas de CORS
- Acesso público (sem autenticação)
- Cache: 24 horas

**Uso**: `http://localhost:5000/media/static/peladas/1/logo.jpg`

---

## Navegação Hierárquica

### Estrutura de Navegação

```
/ (raiz)
  └── /peladas (lista)
      └── /peladas/<id> (perfil)
          ├── /peladas/<id>/temporadas (lista)
          │   └── /temporadas/<id> (detalhe)
          │       ├── /temporadas/<id>/rodadas (lista)
          │       │   └── /rodadas/<id> (detalhe - inclui partidas)
          │       │       └── /partidas/<id> (detalhe)
          │       ├── /temporadas/<id>/times (lista)
          │       │   └── /times/<id> (detalhe)
          │       └── /temporadas/<id>/ranking (hub)
          │           ├── /temporadas/<id>/ranking/times
          │           ├── /temporadas/<id>/ranking/artilheiros
          │           └── /temporadas/<id>/ranking/assistencias
          └── /peladas/<id>/jogadores (lista)
              └── /jogadores/<id>/edit
```

### Bottom Navigation (Mobile)

**Itens fixos**:
1. Peladas (sempre ativo se não houver contexto)
2. Jogadores (ativo se houver `_pelada_id`)
3. Partidas (ativo se houver `_rodada_id`, link para `/rodadas/<id>`)
4. Rankings (ativo se houver `_temporada_id`)
5. Menu (sempre disponível)

**Variáveis de contexto** (definidas em templates):
- `_pelada_id`: ID da pelada atual
- `_temporada_id`: ID da temporada atual
- `_rodada_id`: ID da rodada atual

---

## Tecnologias Utilizadas

### Backend
- **Flask 3.0.3**: Framework web Python
- **Jinja2**: Template engine
- **Requests 2.32.3**: Cliente HTTP
- **Pillow 10.0.0**: Processamento de imagens

### Frontend
- **Tailwind CSS**: Framework CSS utility-first
- **Lucide Icons**: Biblioteca de ícones
- **HTMX 1.9.10**: Interações dinâmicas sem JavaScript complexo
- **html2canvas 1.4.1**: Captura de screenshots

### Recursos Externos
- **Google Fonts (Poppins)**: Fonte customizada
- **n8n Webhook**: Geração de imagens editadas

### Configurações Mobile
- **Viewport**: `width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no`
- **PWA Meta Tags**: `apple-mobile-web-app-capable`, `mobile-web-app-capable`
- **CSS Mobile**: Font-size 16px para inputs (previne zoom iOS), touch-action manipulation

---

## Observações Importantes

### 1. Tratamento de Erros

- **ApiError**: Exceção customizada para erros da API
- **401/403**: Limpa sessão e redireciona para login
- **404/500**: Renderiza página de erro amigável (nunca mostra stacktrace)
- **Flash Messages**: Sistema de mensagens temporárias (sucesso/erro)

### 2. Paginação

- Padrão: `page=1, per_page=10` (configurável)
- Algumas listas usam `per_page=50` ou `per_page=200` para buscar todos

### 3. Filtros de Template (Jinja2)

- `slug`: Converte texto para URL-friendly
- `data_br`: Formata data no padrão brasileiro (DD/MM/YYYY)

### 4. Compatibilidade de Dados

- APIs podem retornar dados em formatos diferentes (lista vs dict)
- Código tenta múltiplos formatos para compatibilidade:
  ```python
  if isinstance(data, list):
      items = data
  elif isinstance(data, dict):
      items = data.get("ranking", data.get("data", []))
  ```

### 5. Sessão Flask

- Armazena: `access_token`, `refresh_token`, `recent_votacoes`
- Secret key: `"super-secret-key"` (deve ser alterado em produção)

---

## Próximos Passos para React Native

### 1. Estrutura de Navegação
- Implementar navegação hierárquica similar (React Navigation)
- Bottom tabs para mobile
- Deep linking para rotas públicas

### 2. Autenticação
- AsyncStorage para tokens
- Interceptor HTTP para adicionar Authorization header
- Refresh token automático

### 3. Upload de Arquivos
- `react-native-image-picker` ou `expo-image-picker`
- FormData para multipart/form-data
- Progress indicator

### 4. Estado Global
- Context API ou Redux para:
  - Autenticação
  - Contexto atual (pelada_id, temporada_id, rodada_id)
  - Cache de dados

### 5. Componentes Reutilizáveis
- Card component
- Ranking table
- Form inputs
- Modal
- Toast notifications

### 6. Funcionalidades Especiais
- Screenshot: `react-native-view-shot`
- Compartilhamento: `react-native-share`
- Busca flexível: Implementar lógica similar
- Agrupamento por posição: Implementar lógica similar

---

**Documento gerado em**: 2025-01-27
**Versão**: 1.0.0

