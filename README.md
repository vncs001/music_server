# music_server

Servidor de downloads do **8bit player** (`../music_app`). O app busca uma música, o servidor
baixa o áudio do YouTube com o **yt-dlp**, converte para MP3 e o celular puxa o arquivo.

```
celular ──HTTPS──▶ nginx do painel da VPS ──▶ servidor Python :8000 (FastAPI + yt-dlp + ffmpeg)
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
Dockerfile, docker-compose.yml   deploy na VPS
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

## Deploy na VPS (painel com deploy por Git)

O painel da VPS faz o HTTPS com o nginx dele; o `docker-compose.yml` sobe só o servidor na
porta 8000 (aberta apenas para a própria VPS, `127.0.0.1`).

1. **Deploy a partir do Git** com este repositório. Variáveis:
   - `API_TOKEN`: gere e **guarde uma cópia** (vai no app também). Marque como segredo, usada "ao rodar".
   - `MAX_FILE_AGE_HOURS=24`, `MAX_PARALLEL_DOWNLOADS=2` (use 1 se a VPS tiver 1 GB de RAM).
2. **Portas e Domínios**: aponte um domínio/subdomínio para a **porta 8000** e ative o HTTPS.
3. Teste no navegador: `https://SEU_DOMINIO/health` deve mostrar `{"ok":true}`.
4. No app: **CONFIG → Servidor de downloads** → `https://SEU_DOMINIO` + o token → SALVAR E TESTAR.

Sem painel (VPS "crua"): instale o Docker (`curl -fsSL https://get.docker.com | sh`), crie um `.env`
a partir do `.env.example`, rode `docker compose up -d --build` e coloque um proxy com HTTPS
(nginx ou Caddy) apontando para `127.0.0.1:8000`.

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
