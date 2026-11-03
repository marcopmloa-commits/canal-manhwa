"""Envia um Short ao YouTube como PRIVADO (aprovação manual antes de publicar).

Requer YT_CLIENT_ID, YT_CLIENT_SECRET e o refresh token, lido de YT_REFRESH_TOKEN
ou do arquivo indicado em --token.

Uso: python3 youtube_upload.py roteiros/001_the_boxer.json saida/001_the_boxer [--token ARQUIVO]
"""
import json, os, sys, urllib.error, urllib.parse, urllib.request


def refresh_token():
    if "--token" in sys.argv:
        return open(sys.argv[sys.argv.index("--token") + 1]).read().strip()
    return os.environ["YT_REFRESH_TOKEN"]


def access_token():
    data = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": refresh_token(), "grant_type": "refresh_token"}).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data) as r:
        return json.load(r)["access_token"]


def call(req):
    try:
        with urllib.request.urlopen(req) as r:
            return r.headers, r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"Erro {e.code}: {e.read().decode()[:800]}")


def main():
    script = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    video = os.path.join(out, "short.mp4")
    thumb = os.path.join(out, "thumbnail.jpg")
    tok = access_token()
    meta = {
        "snippet": {"title": script["titulo"][:100], "description": script["descricao"],
                    "tags": script.get("tags", []), "categoryId": "1", "defaultLanguage": "pt-BR"},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
    }
    size = os.path.getsize(video)
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        json.dumps(meta).encode(), method="POST", headers={
            "Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})
    upload_url = call(req)[0]["Location"]
    with open(video, "rb") as f:
        req = urllib.request.Request(upload_url, f.read(), method="PUT", headers={
            "Authorization": f"Bearer {tok}", "Content-Type": "video/mp4"})
    vid = json.loads(call(req)[1])["id"]
    print(f"Enviado como PRIVADO: https://youtu.be/{vid}", flush=True)
    if os.path.exists(thumb):
        req = urllib.request.Request(
            f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={vid}",
            open(thumb, "rb").read(), method="POST",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "image/jpeg"})
        try:
            urllib.request.urlopen(req).close()
            print("Thumbnail definida.")
        except urllib.error.HTTPError as e:  # canais não verificados não podem usar thumbnail personalizada
            print(f"Thumbnail não aplicada ({e.code}): {e.read().decode()[:300]}")
    json.dump({"video_id": vid}, open(os.path.join(out, "youtube.json"), "w"))


if __name__ == "__main__":
    main()
