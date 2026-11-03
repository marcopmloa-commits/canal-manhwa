"""Envia um Short gerado por make_short.py para o YouTube (YouTube Data API v3).

Uso:
  python3 youtube.py auth                    # 1x, no SEU computador: gera o refresh token
  python3 youtube.py upload saida/001_the_boxer [--privacidade private|unlisted|public]
  python3 youtube.py checar                  # testa as credenciais e mostra o canal

Credenciais (variáveis de ambiente):
  YT_CLIENT_ID, YT_CLIENT_SECRET  -> cliente OAuth "App para computador" do Google Cloud
  YT_REFRESH_TOKEN                -> gerado pelo comando `auth`

Por padrão o vídeo sobe como PRIVADO: todo vídeo passa por aprovação antes de ir ao ar.
"""
import argparse, http.server, json, os, secrets, sys, urllib.parse, webbrowser
import requests

SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD_API = "https://www.googleapis.com/upload/youtube/v3"

_CA = "/root/.ccr/ca-bundle.crt"  # certificado do proxy do ambiente cloud
VERIFY = _CA if os.path.exists(_CA) else True


def env(name):
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Falta a variável de ambiente {name}. Veja o README (seção YouTube).")
    return v


# ---------- auth: roda uma vez, no computador de quem é dono do canal ----------
def cmd_auth(_):
    cid, secret = env("YT_CLIENT_ID"), env("YT_CLIENT_SECRET")
    state, result = secrets.token_urlsafe(16), {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("Pronto, pode fechar esta aba e voltar ao terminal.".encode())

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    redirect = f"http://127.0.0.1:{srv.server_port}"
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code",
        "scope": SCOPES, "access_type": "offline", "prompt": "consent", "state": state})
    print("Abra este link, entre com a conta do canal e autorize:\n\n" + url + "\n")
    webbrowser.open(url)
    while "code" not in result and "error" not in result:
        srv.handle_request()
    if result.get("error") or result.get("state") != state:
        sys.exit(f"Autorização falhou: {result.get('error', 'state inválido')}")
    r = requests.post(TOKEN_URL, data={
        "code": result["code"], "client_id": cid, "client_secret": secret,
        "redirect_uri": redirect, "grant_type": "authorization_code"})
    r.raise_for_status()
    tok = r.json().get("refresh_token")
    if not tok:
        sys.exit("O Google não devolveu refresh token. Remova o acesso do app em "
                 "myaccount.google.com/permissions e rode de novo.")
    print("Refresh token (guarde como segredo YT_REFRESH_TOKEN no ambiente; não cole no chat):\n")
    print(tok)


# ---------- token de acesso ----------
def access_token():
    r = requests.post(TOKEN_URL, verify=VERIFY, data={
        "client_id": env("YT_CLIENT_ID"), "client_secret": env("YT_CLIENT_SECRET"),
        "refresh_token": env("YT_REFRESH_TOKEN"), "grant_type": "refresh_token"})
    if r.status_code != 200:
        sys.exit(f"Não consegui renovar o token ({r.status_code}): {r.text}\n"
                 "Se o app está em modo 'Teste' no Google Cloud, o token expira em 7 dias: "
                 "rode `auth` de novo ou publique o app (Tela de consentimento → Publicar).")
    return r.json()["access_token"]


def cmd_checar(_):
    h = {"Authorization": f"Bearer {access_token()}"}
    r = requests.get(f"{API}/channels", params={"part": "snippet,statistics", "mine": "true"},
                     headers=h, verify=VERIFY)
    r.raise_for_status()
    for c in r.json().get("items", []):
        s = c["statistics"]
        print(f"Conectado ao canal: {c['snippet']['title']} ({c['id']}) — "
              f"{s.get('subscriberCount', '?')} inscritos, {s.get('videoCount', '?')} vídeos")


# ---------- upload ----------
def read_post(path):
    """Lê post.txt (blocos TÍTULO:, DESCRIÇÃO:, TAGS:)."""
    sec, cur = {}, None
    for line in open(path, encoding="utf-8").read().splitlines():
        key = line.strip().rstrip(":").upper()
        if line.strip().endswith(":") and key in ("TÍTULO", "TITULO", "DESCRIÇÃO", "DESCRICAO", "TAGS"):
            cur = key.replace("Í", "I").replace("Ç", "C").replace("Ã", "A")
            sec[cur] = []
        elif cur:
            sec[cur].append(line)
    get = lambda k: "\n".join(sec.get(k, [])).strip()
    tags = [t.strip() for t in get("TAGS").split(",") if t.strip()]
    return get("TITULO"), get("DESCRICAO"), tags


def cmd_upload(a):
    video = os.path.join(a.pasta, "short.mp4")
    thumb = os.path.join(a.pasta, "thumbnail.jpg")
    if not os.path.exists(video):
        sys.exit(f"Não achei {video}. Gere antes com make_short.py.")
    title, desc, tags = read_post(os.path.join(a.pasta, "post.txt"))
    if not title:
        sys.exit("post.txt sem TÍTULO.")
    if len(title) > 100:
        sys.exit(f"Título com {len(title)} caracteres (máx. 100).")

    h = {"Authorization": f"Bearer {access_token()}"}
    meta = {
        "snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "24",
                    "defaultLanguage": "pt-BR", "defaultAudioLanguage": "pt-BR"},
        "status": {"privacyStatus": a.privacidade, "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": True},  # narração gerada por TTS
    }
    size = os.path.getsize(video)
    r = requests.post(f"{UPLOAD_API}/videos", verify=VERIFY,
                      params={"uploadType": "resumable", "part": "snippet,status"},
                      headers={**h, "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Type": "video/mp4",
                               "X-Upload-Content-Length": str(size)},
                      data=json.dumps(meta))
    if r.status_code != 200:
        sys.exit(f"Falha ao iniciar upload ({r.status_code}): {r.text}")
    with open(video, "rb") as f:
        r = requests.put(r.headers["Location"], data=f, verify=VERIFY,
                         headers={**h, "Content-Type": "video/mp4", "Content-Length": str(size)})
    if r.status_code not in (200, 201):
        sys.exit(f"Falha no envio do vídeo ({r.status_code}): {r.text}")
    vid = r.json()["id"]
    print(f"Vídeo enviado ({a.privacidade}): https://youtu.be/{vid}")
    print(f"Revisar no Studio: https://studio.youtube.com/video/{vid}/edit")

    if os.path.exists(thumb):
        with open(thumb, "rb") as f:
            t = requests.post(f"{UPLOAD_API}/thumbnails/set", params={"videoId": vid},
                              headers={**h, "Content-Type": "image/jpeg"}, data=f, verify=VERIFY)
        if t.status_code == 200:
            print("Thumbnail aplicada.")
        else:
            print(f"Thumbnail não aplicada ({t.status_code}). Thumbnails personalizadas exigem "
                  "canal verificado por telefone (youtube.com/verify).")
    json.dump({"video_id": vid, "privacidade": a.privacidade},
              open(os.path.join(a.pasta, "youtube.json"), "w"), indent=2)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth").set_defaults(f=cmd_auth)
    sub.add_parser("checar").set_defaults(f=cmd_checar)
    u = sub.add_parser("upload")
    u.add_argument("pasta")
    u.add_argument("--privacidade", default="private", choices=["private", "unlisted", "public"])
    u.set_defaults(f=cmd_upload)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
