# music_server

Servidor de downloads do **8bit player** (`../music_app`). O app busca uma música, o servidor
baixa o áudio do YouTube com o **yt-dlp**, converte para MP3 e o celular puxa o arquivo.

```
celular ──HTTPS──▶ Caddy (certificado grátis) ──▶ servidor Python (FastAPI + yt-dlp + ffmpeg)
```

> Baixar do YouTube vai contra os termos de uso dele. Uso pessoal, por sua conta.

## Estrutura

```
app/
  main.py               rotas da API (create_app monta tudo)
  config.py             Settings: lê o .env
  models.py             formatos JSON (SearchResult, JobInfo...)
  services/
    search.py           YtDlpSearch (sem chave) / YouTubeApiSearch (com YOUTUBE_API_KEY)
    downloader.py       Downloader: yt-dlp + ffmpeg -> "Artista - Titulo.mp3"
    jobs.py             JobManager: fila de downloads em segundo plano + limpeza
tests/                  testes sem internet (busca e download falsos)
Dockerfile, docker-compose.yml, Caddyfile   deploy na VPS
scripts/update.sh       atualiza código + yt-dlp na VPS
```

## API

Todas as rotas, menos `/health`, exigem `Authorization: Bearer <API_TOKEN>`.

| Rota | O que faz |
|---|---|
| `GET /health` | servidor vivo? (sem token) |
| `GET /check` | token certo? (botão TESTAR do app) |
| `GET /search?q=nome&limit=5` | busca no YouTube |
| `POST /downloads` `{"video_id": "..."}` | começa a baixar, devolve o job |
| `GET /downloads/{id}` | status: `queued` → `downloading` → `converting` → `done` / `error`, com `progress` 0–1 |
| `GET /downloads/{id}/file` | o MP3 pronto |

Documentação interativa: `https://SEU_DOMINIO/docs`.

## Deploy na VPS

Qualquer VPS Linux com 1 GB de RAM serve. Na VPS:

```bash
# 1. Docker (uma vez)
curl -fsSL https://get.docker.com | sh

# 2. Código
git clone <seu-repositorio> music_server && cd music_server
cp .env.example .env
nano .env        # preencha API_TOKEN e DOMAIN (veja abaixo)

# 3. Subir
docker compose up -d --build
curl https://SEU_DOMINIO/health      # deve responder {"ok":true}
```

- **API_TOKEN**: gere com `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.
- **DOMAIN**: sem domínio próprio, use o IP da VPS com sslip.io (IP `203.0.113.5` vira
  `203-0-113-5.sslip.io`). O Caddy tira o certificado HTTPS sozinho; as portas 80 e 443 precisam
  estar abertas no firewall da VPS.

No app: **CONFIG → Servidor** → endereço `https://SEU_DOMINIO` e o mesmo token.

### Quando os downloads começarem a falhar

O YouTube muda a proteção com frequência e o yt-dlp acompanha. Na VPS:

```bash
./scripts/update.sh    # git pull + reconstrói a imagem com o yt-dlp mais novo
```

Se o erro for **"Sign in to confirm you're not a bot"**, o YouTube bloqueou o IP da VPS
(acontece com IPs de datacenter). Exporte os cookies de uma conta do YouTube (pode ser uma conta
secundária) com uma extensão "Get cookies.txt", salve em `secrets/cookies.txt` e descomente
`COOKIES_FILE=/secrets/cookies.txt` no `.env`. Depois `docker compose up -d`.

## Desenvolvimento local

Precisa de Python 3.12 e do `ffmpeg` no PATH (`sudo apt install ffmpeg`).

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest                       # testes

cp .env.example .env                             # preencha API_TOKEN
.venv/bin/uvicorn app.main:create_app_from_env --factory --reload
```

## Busca: com ou sem chave

- **Sem chave (padrão)**: o yt-dlp busca direto, sem cota.
- **YouTube Data API v3**: preencha `YOUTUBE_API_KEY`. Grátis, 10.000 unidades/dia e cada busca
  custa 100, então dá ~100 buscas/dia. Crie no Google Cloud Console → ative "YouTube Data API v3"
  → Credenciais → Chave de API.

Origem: protótipo `../music_downloader/Music-01/index.js` (a busca pela Data API virou
`YouTubeApiSearch`).
