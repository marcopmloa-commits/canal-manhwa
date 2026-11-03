"""Autoriza o envio de vídeos ao YouTube pelo fluxo de código curto (google.com/device).

Requer YT_CLIENT_ID e YT_CLIENT_SECRET de um cliente OAuth do tipo
"TVs e dispositivos de entrada limitada".

Uso: python3 youtube_auth.py ARQUIVO_SAIDA
Grava o refresh token em ARQUIVO_SAIDA (nunca no terminal) para você copiá-lo
para a variável YT_REFRESH_TOKEN nas configurações do ambiente.
"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

SCOPE = "https://www.googleapis.com/auth/youtube"  # o fluxo de dispositivo não aceita youtube.upload


def post(url, data):
    req = urllib.request.Request(url, urllib.parse.urlencode(data).encode())
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.load(e)


def main():
    out = sys.argv[1]
    cid, secret = os.environ["YT_CLIENT_ID"], os.environ["YT_CLIENT_SECRET"]
    dev = post("https://oauth2.googleapis.com/device/code", {"client_id": cid, "scope": SCOPE})
    if "device_code" not in dev:
        sys.exit(f"Erro ao pedir código: {dev}")
    print(f"Abra {dev['verification_url']} e digite o código: {dev['user_code']}", flush=True)
    interval, deadline = dev.get("interval", 5), time.time() + dev["expires_in"]
    while time.time() < deadline:
        time.sleep(interval)
        tok = post("https://oauth2.googleapis.com/token", {
            "client_id": cid, "client_secret": secret, "device_code": dev["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
        err = tok.get("error")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 5
            continue
        if err:
            sys.exit(f"Autorização falhou: {err} {tok.get('error_description', '')}")
        fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(tok["refresh_token"] + "\n")
        print(f"Autorizado. Refresh token gravado em {out}", flush=True)
        return
    sys.exit("O código expirou. Rode de novo.")


if __name__ == "__main__":
    main()
