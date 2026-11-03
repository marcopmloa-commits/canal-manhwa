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
`tamanho` (fonte, opcional), `imagem` (caminho relativo ao JSON, opcional), `foco` (0–1, recorte vertical).
Na raiz: `titulo`, `descricao`, `tags`, `thumb`, `thumb_sub`, `thumb_imagem`, `voz`, `velocidade`.

## Regras do canal

- Conferir fatos em fonte oficial antes de postar.
- Sem painéis de scan/pirataria: só capa oficial, pôster/visual do anime ou frames parados do trailer (sem áudio). 3–5 imagens por Short, sempre com narração por cima.
- Trilha gerada pelo próprio código (sem direitos autorais).
- Todo vídeo passa por aprovação antes de ir ao ar.
