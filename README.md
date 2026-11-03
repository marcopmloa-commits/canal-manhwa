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

## Publicar no YouTube

`youtube.py` envia o Short pela YouTube Data API v3. Ele sobe **privado** por padrão, para passar pela aprovação.

1. No [Google Cloud Console](https://console.cloud.google.com/): crie um projeto, ative a **YouTube Data API v3**,
   configure a tela de consentimento OAuth (tipo Externo, com seu e-mail como usuário de teste) e crie um
   cliente OAuth do tipo **App para computador**.
2. Para o token não expirar em 7 dias: na tela de consentimento, clique em **Publicar app** (não precisa de verificação para uso próprio).
3. No seu computador, rode uma vez:
   ```bash
   YT_CLIENT_ID=... YT_CLIENT_SECRET=... python3 youtube.py auth
   ```
4. Guarde `YT_CLIENT_ID`, `YT_CLIENT_SECRET` e `YT_REFRESH_TOKEN` como segredos do ambiente cloud.

```bash
python3 youtube.py checar
python3 youtube.py upload saida/001_the_boxer
```

Observação: em projetos de API não auditados pelo Google, o YouTube trava os vídeos enviados como privados.
Isso combina com a regra de aprovação: publique pelo YouTube Studio depois de revisar.
