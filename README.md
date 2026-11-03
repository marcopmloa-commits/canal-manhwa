# Canal Manhwa

Canal dark de notícias, análises e rankings de manhwa (Shorts + vídeos longos).

## Gerar um Short

```bash
pip install -r requirements.txt
python3 make_short.py roteiros/001_the_boxer.json saida/001_the_boxer
```

Saída em `saida/<nome>/`: `short.mp4` (1080x1920), `thumbnail.jpg`, `post.txt` e `tempos.json`.

## Roteiro (JSON)

Cada item de `segmentos`: `fala` (narração), `destaque` (título na tela), `sub` (selo, opcional),
`tamanho` (fonte, opcional), `imagem` (caminho relativo ao JSON, opcional), `foco` (0–1, recorte vertical),
`video` (trecho de vídeo no lugar da imagem, sem o áudio original; até 6 s, depois segura o último quadro) e `video_inicio` (segundo de início no arquivo).
Na raiz: `titulo`, `descricao`, `tags`, `thumb`, `thumb_sub`, `thumb_imagem`, `voz`, `velocidade`.

## Regras do canal

- Conferir fatos em fonte oficial antes de postar.
- Sem painéis de scan/pirataria: só capa oficial, pôster/visual do anime, frames do trailer ou trechos curtos de trailer/PV oficial (sem o áudio original, até 6 s cada, no máximo 3 por Short). 3–5 imagens/trechos por Short, sempre com narração por cima.
- Trechos de vídeo ficam em `roteiros/videos/<NNN_slug>/` (o YouTube bloqueia download a partir da nuvem: se não houver arquivo, usar imagens).
- Trilha gerada pelo próprio código (sem direitos autorais).
- Produção automática: 3 Shorts por dia, publicados sem revisão manual (agendados para 12h, 16h e 19h). Ver `AUTOMACAO.md`.

## Enviar ao YouTube

Requer `YT_CLIENT_ID` e `YT_CLIENT_SECRET` (cliente OAuth "TVs e dispositivos de entrada limitada") nas variáveis do ambiente.

```bash
python3 youtube_auth.py /caminho/fora/do/repo/yt_token.txt   # mostra um código para digitar em google.com/device
python3 youtube_upload.py roteiros/001_the_boxer.json saida/001_the_boxer --token /caminho/fora/do/repo/yt_token.txt
```

Por padrão o vídeo sobe como **privado**. Use `--publico` para publicar na hora ou `--publicar-em 2026-11-04T12:00:00-03:00` para agendar. Para não autorizar de novo,
salve o token como `YT_REFRESH_TOKEN` nas variáveis do ambiente (aí o `--token` é dispensável).
