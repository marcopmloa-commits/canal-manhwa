# Produção automática diária (3 Shorts)

Executado todo dia às 00:00 (horário de Brasília) por uma tarefa agendada do Claude Code.
Os vídeos são publicados automaticamente, sem revisão manual: por isso as regras abaixo são obrigatórias.

## Passo a passo

1. **Branch:** trabalhar em `short-the-boxer-imagens` (`git fetch origin short-the-boxer-imagens && git checkout short-the-boxer-imagens`).
2. **Pré-checagem:** `YT_CLIENT_ID`, `YT_CLIENT_SECRET` e `YT_REFRESH_TOKEN` precisam existir (nunca imprimir os valores).
   Se faltar algum, parar e avisar.
3. **Histórico:** ler `roteiros/*.json` e `historico.md` para não repetir manhwa nem formato dos últimos 7 dias.
4. **Escolher 3 temas**, de formatos diferentes, e **pelo menos 1 por dia deve ser História**:
   - **História** (conta a trama de um manhwa como narrativa: premissa, virada do 1º arco e um gancho no final
     tipo "e aí ele descobre que…"; sem spoilers do final; avisar "sem spoiler do final" no 1º segmento;
     pode virar série "Parte 1/2/3" para obras longas, registrando a parte em `historico.md`);
   - **Notícia** (anime/live-action anunciado, trailer, data de estreia, fim/retorno de temporada, prêmio);
   - **Ranking/lista** (ex.: "5 manhwas de luta subestimados", "manhwas parecidos com X");
   - **Explicação/curiosidade** (quem é tal personagem, o que é tal sistema/poder, origem da obra, autor).
   Sem notícia nova e confirmada no dia, trocar por outro formato: nunca inventar notícia.
   Para História, conferir a trama na sinopse oficial (Webtoon/Tapas/Tappytoon/editora) e em resumos confiáveis.
5. **Fatos:** conferir cada afirmação em fonte oficial (editora/plataforma: Webtoon, Kakao, Tapas, Tappytoon;
   estúdio/distribuidora: Crunchyroll, Netflix etc.; perfis oficiais). Na dúvida, cortar a frase.
   Anotar as fontes em `historico.md`.
6. **Imagens:** só capa oficial, pôster/visual oficial ou frame parado de trailer oficial, salvas em
   `roteiros/img/<NNN_slug>/`. Nada de painel de scan/pirataria. Sem imagem oficial, escolher outro tema.
   **Vídeos:** se houver trailer/PV oficial disponível como arquivo (ex.: colocado pelo dono em `roteiros/videos/`,
   ou baixável de fonte oficial), usar até 3 trechos de no máximo 6 s (campo `video` + `video_inicio`), sem o áudio
   original e com narração por cima; registrar a origem em `fontes_imagens`. O YouTube bloqueia download a
   partir da nuvem, mas **vídeos de contas oficiais no X funcionam** com `python3 -m yt_dlp <link do post>` (ex.: @sololeveling_pr).
   Salvar sem áudio em `roteiros/videos/<obra>/` (`ffmpeg -i x.mp4 -an -c:v copy`), evitar trechos com texto em
   japonês, créditos ou rostos de artistas. Se falhar, seguir só com imagens (não usar reupload não oficial).
7. **Roteiro:** `roteiros/<NNN>_<slug>.json` no mesmo formato de `001_the_boxer.json`
   (numeração sequencial; 6–7 segmentos; 30–50 s de narração; 3–5 imagens; gancho forte no 1º segmento;
   pergunta + "segue o canal" no final; título com emoji e `#manhwa`; descrição com hashtags; tags).
8. **Gerar:** `python3 make_short.py roteiros/<NNN>_<slug>.json saida/<NNN>_<slug>`.
9. **Enviar agendado** (público sozinho no horário):
   - vídeo 1 → 12:00, vídeo 2 → 16:00, vídeo 3 → 19:00 do mesmo dia, horário de Brasília (`-03:00`):
   `python3 youtube_upload.py roteiros/<NNN>_<slug>.json saida/<NNN>_<slug> --publicar-em 2026-11-04T12:00:00-03:00`
   - Thumbnail: o script tenta; se der 403, seguir (o canal ainda não tem o recurso liberado).
10. **Registrar:** acrescentar em `historico.md` a data, os 3 temas, formatos, links e fontes; commitar roteiros,
    imagens, `saida/*/youtube.json`, `post.txt`, `tempos.json`, `thumbnail.jpg` e `historico.md`; push no branch.
11. **Avisar** o dono do canal com os 3 links e horários.

## Cota da API

Cada envio gasta ~1.600 das 10.000 unidades diárias: 3 vídeos/dia ficam bem dentro do limite.
