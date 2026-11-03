"""Gera um YouTube Short (1080x1920) a partir de um roteiro em JSON.

Uso: python3 make_short.py roteiro.json pasta_saida
"""
import asyncio, json, math, os, ssl, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import edge_tts.communicate as tts

_CA = "/root/.ccr/ca-bundle.crt"  # certificado do proxy do ambiente cloud
if os.path.exists(_CA):
    tts._SSL_CTX = ssl.create_default_context(cafile=_CA)

W, H, FPS = 1080, 1920, 30
FONT_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf"
RED = (230, 30, 45)
YELLOW = (255, 214, 10)
WHITE = (245, 245, 245)


def font(path, size, _c={}):
    k = (path, size)
    if k not in _c:
        _c[k] = ImageFont.truetype(path, size)
    return _c[k]


# ---------- 1. narração + tempos de cada palavra ----------
async def narrate(segments, voice, rate, out_mp3):
    text = " ".join(s["fala"] for s in segments)
    com = tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words, audio = [], bytearray()
    async for ch in com.stream():
        if ch["type"] == "audio":
            audio += ch["data"]
        elif ch["type"] == "WordBoundary":
            words.append({"w": ch["text"], "t0": ch["offset"] / 1e7,
                          "t1": (ch["offset"] + ch["duration"]) / 1e7})
    open(out_mp3, "wb").write(audio)
    # em que palavra começa cada segmento
    starts, idx = [], 0
    for s in segments:
        starts.append(words[min(idx, len(words) - 1)]["t0"])
        idx += len(s["fala"].split())
    return words, starts


def duration(path):
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]))


# ---------- 2. trilha sintetizada (sem direitos autorais) ----------
def make_music(path, dur, hits, sr=44100):
    t = np.arange(int(dur * sr)) / sr
    drone = 0.18 * np.sin(2 * np.pi * 55 * t) + 0.08 * np.sin(2 * np.pi * 82.4 * t)
    drone *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.1 * t)
    beat = np.zeros_like(t)
    bpm = 92
    for k in np.arange(0, dur, 60 / bpm):  # batida grave tipo coração
        for off, amp in ((0, 1.0), (0.18, 0.6)):
            i = int((k + off) * sr)
            n = min(int(0.25 * sr), len(t) - i)
            if n <= 0:
                continue
            tt = np.arange(n) / sr
            beat[i:i + n] += amp * 0.5 * np.sin(2 * np.pi * (60 * np.exp(-tt * 18) + 40) * tt) * np.exp(-tt * 14)
    boom = np.zeros_like(t)
    for h in hits:  # impacto nas trocas de cena
        i = int(h * sr)
        n = min(int(0.9 * sr), len(t) - i)
        if n <= 0:
            continue
        tt = np.arange(n) / sr
        boom[i:i + n] += 0.9 * np.sin(2 * np.pi * (90 * np.exp(-tt * 6) + 30) * tt) * np.exp(-tt * 5)
        boom[i:i + n] += 0.15 * np.random.randn(n) * np.exp(-tt * 30)
    mix = drone + beat + boom
    fade = np.minimum(1, np.minimum(t / 0.5, (dur - t) / 1.0))
    mix = np.clip(mix * fade / (np.abs(mix).max() + 1e-9), -1, 1)
    pcm = (mix * 32767 * 0.9).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())


# ---------- 3. visual ----------
def base_layers():
    yy, xx = np.mgrid[0:H, 0:W]
    glow = np.exp(-(((xx - W / 2) / 700) ** 2 + ((yy - H * 0.42) / 900) ** 2))
    bg = np.zeros((H, W, 3), np.float32)
    bg[..., 0] = 12 + 90 * glow
    bg[..., 1] = 8 + 6 * glow
    bg[..., 2] = 12 + 10 * glow
    vignette = 1 - 0.65 * np.clip(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2, 0, 1)
    bg *= vignette[..., None]
    rng = np.random.default_rng(1)
    grains = [rng.normal(0, 9, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
    return bg, grains


def rope_layer(phase):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k, y in enumerate((1360, 1470, 1580)):  # cordas do ringue
        sag = 40 + 10 * math.sin(phase + k)
        pts = [(x, y + sag * math.sin(math.pi * x / W)) for x in range(-20, W + 40, 40)]
        d.line(pts, fill=(*RED, 70), width=10)
        d.line([(px, py - 3) for px, py in pts], fill=(255, 120, 120, 40), width=2)
    return im


def text_w(f, s):
    return f.getbbox(s)[2] - f.getbbox(s)[0]


def wrap(s, f, maxw):
    lines, cur = [], ""
    for w in s.split():
        test = (cur + " " + w).strip()
        if text_w(f, test) <= maxw or not cur:
            cur = test
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    return lines


def draw_headline(frame, seg, local_t, cy=620, escala=1.0):
    pop = min(1, local_t / 0.22)
    scale = 1.35 - 0.35 * (1 - (1 - pop) ** 3)
    size = int(seg.get("tamanho", 150) * scale * escala)
    f = font(FONT_BLACK, size)
    lines = wrap(seg["destaque"].upper(), f, W - 140)
    widest = max(text_w(f, ln) for ln in lines)
    if widest > W - 140:  # palavra única larga demais: reduz a fonte
        size = int(size * (W - 140) / widest)
        f = font(FONT_BLACK, size)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    lh = int(size * 1.05)
    y0 = cy - lh * len(lines) // 2
    for i, ln in enumerate(lines):
        x = (W - text_w(f, ln)) // 2
        col = YELLOW if i == len(lines) - 1 and len(lines) > 1 else WHITE
        d.text((x + 8, y0 + i * lh + 10), ln, font=f, fill=(*RED, 230))  # sombra vermelha deslocada
        d.text((x, y0 + i * lh), ln, font=f, fill=col, stroke_width=6, stroke_fill=(0, 0, 0))
    if "sub" in seg:
        fs = font(FONT_BOLD, 52)
        sub = seg["sub"].upper()
        tw = text_w(fs, sub)
        y = y0 + len(lines) * lh + 40
        d.rounded_rectangle(((W - tw) // 2 - 30, y - 12, (W + tw) // 2 + 30, y + 72), 14, fill=(*RED, 235))
        d.text(((W - tw) // 2, y), sub, font=fs, fill=WHITE)
    alpha = min(1, local_t / 0.12)
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda a: int(a * alpha)))
    frame.alpha_composite(layer)


def draw_captions(frame, words, t, y=1100):
    # agrupa palavras em blocos de até 3, mostra o bloco atual e destaca a palavra falada
    groups = [words[i:i + 3] for i in range(0, len(words), 3)]
    cur = None
    for g in groups:
        if g[0]["t0"] - 0.05 <= t <= g[-1]["t1"] + 0.25:
            cur = g
    if not cur:
        return
    f = font(FONT_BLACK, 82)
    d = ImageDraw.Draw(frame)
    parts = [w["w"].upper() for w in cur]
    space = 24
    total = sum(text_w(f, p) for p in parts) + space * (len(parts) - 1)
    if total > W - 100:
        f = font(FONT_BLACK, int(82 * (W - 100) / total))
        total = sum(text_w(f, p) for p in parts) + space * (len(parts) - 1)
    x = (W - total) // 2
    for w, p in zip(cur, parts):
        on = w is max((x for x in cur if x["t0"] <= t), key=lambda x: x["t0"], default=None)
        col = YELLOW if on else WHITE
        d.text((x, y - (6 if on else 0)), p, font=f, fill=col, stroke_width=8, stroke_fill=(0, 0, 0))
        x += text_w(f, p) + space


def draw_chrome(frame, t, dur, tag):
    d = ImageDraw.Draw(frame)
    f = font(FONT_BOLD, 40)
    tw = text_w(f, tag)
    d.rounded_rectangle((60, 150, 60 + tw + 50, 220), 12, fill=(*RED, 255))
    d.text((85, 160), tag, font=f, fill=WHITE)
    d.rectangle((0, H - 14, int(W * t / dur), H), fill=(*RED, 255))


# ---------- imagens (capa / visual oficial) ----------
CARD = (60, 270, 1020, 1010)  # x0, y0, x1, y1 do quadro da imagem


def cover(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((max(w, round(im.width * r)), max(h, round(im.height * r))), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def prep_image(path, base_dir, foco=0.5):
    """Prepara fundo desfocado + imagem nítida do quadro (com folga p/ zoom)."""
    im = Image.open(os.path.join(base_dir, path)).convert("RGB")
    cw, ch = CARD[2] - CARD[0], CARD[3] - CARD[1]
    big = 1.12
    r = max(cw * big / im.width, ch * big / im.height)
    sharp = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    # recorte vertical controlado por "foco" (0 = topo, 1 = base), útil p/ capas em pé
    tw, th = round(cw * big), round(ch * big)
    x = (sharp.width - tw) // 2
    y = round((sharp.height - th) * foco)
    sharp = sharp.crop((x, y, x + tw, y + th))
    blur = cover(im, W // 4, H // 4).filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
    bg = np.asarray(blur, np.float32) * 0.32
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw - 1, ch - 1), 28, fill=255)
    return {"bg": bg, "sharp": sharp, "mask": mask, "size": (cw, ch)}


def prep_video(path, base_dir, inicio=0.0, dur=6.0):
    """Trecho de vídeo (sem áudio) recortado para o quadro; quadros a 15 fps, reaproveitados a 30 fps."""
    cw, ch = CARD[2] - CARD[0], CARD[3] - CARD[1]
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-ss", str(inicio), "-t", str(dur), "-i", os.path.join(base_dir, path),
         "-an", "-vf", f"fps=15,scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch}",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    n = len(raw) // (cw * ch * 3)
    if not n:
        raise SystemExit(f"Vídeo sem quadros: {path}")
    frames = [Image.frombuffer("RGB", (cw, ch), raw[k * cw * ch * 3:(k + 1) * cw * ch * 3]) for k in range(n)]
    blur = cover(frames[0], W // 4, H // 4).filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw - 1, ch - 1), 28, fill=255)
    return {"bg": np.asarray(blur, np.float32) * 0.32, "frames": frames, "mask": mask, "size": (cw, ch)}


def draw_card(frame, img, lt, seg_dur):
    cw, ch = img["size"]
    if "frames" in img:  # trecho de vídeo: segura o último quadro se a fala for mais longa
        crop = img["frames"][min(len(img["frames"]) - 1, max(0, int(lt * 15)))]
        rise = int(60 * (1 - min(1, max(0, lt) / 0.25)) ** 3)
        d = ImageDraw.Draw(frame)
        d.rounded_rectangle((CARD[0] - 8, CARD[1] - 8 + rise, CARD[2] + 8, CARD[3] + 8 + rise), 34, fill=(*RED, 255))
        frame.paste(crop.convert("RGBA"), (CARD[0], CARD[1] + rise), img["mask"])
        return
    p = min(1, max(0, lt / max(seg_dur, 0.1)))
    z = 1.12 - 0.10 * p  # zoom-in lento (Ken Burns)
    sw, sh = img["sharp"].size
    w = cw * 1.12 / z
    h = ch * 1.12 / z
    x0, y0 = (sw - w) / 2, (sh - h) / 2
    crop = img["sharp"].resize((cw, ch), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h))
    # entra subindo
    rise = int(60 * (1 - min(1, lt / 0.25)) ** 3)
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((CARD[0] - 8, CARD[1] - 8 + rise, CARD[2] + 8, CARD[3] + 8 + rise), 34, fill=(*RED, 255))
    frame.paste(crop.convert("RGBA"), (CARD[0], CARD[1] + rise), img["mask"])


def render(script, words, starts, dur, out_mp4, audio_mix, base_dir="."):
    bg, grains = base_layers()
    segs = script["segmentos"]
    ends = starts[1:] + [dur]
    imgs = []
    for k, s in enumerate(segs):
        if s.get("video"):
            imgs.append(prep_video(s["video"], base_dir, s.get("video_inicio", 0), min(6, ends[k] - starts[k] + 0.3)))
        elif s.get("imagem"):
            imgs.append(prep_image(s["imagem"], base_dir, s.get("foco", 0.5)))
        else:
            imgs.append(None)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio_mix,
         "-c:v", "libx264", "-preset", "medium", "-crf", "25", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_mp4],
        stdin=subprocess.PIPE)
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS
        si = max(k for k, s in enumerate(starts) if s <= t + 0.05) if t + 0.05 >= starts[0] else 0
        lt = t - starts[si]
        # leve "respiração" e tremida no impacto
        z = 1 + 0.03 * math.sin(t * 0.6)
        shake = 14 * math.exp(-lt * 9) * math.sin(lt * 70) if si > 0 or lt < 0.5 else 0
        g = grains[i % len(grains)]
        g = np.repeat(np.repeat(g, 2, 0), 2, 1)
        img = imgs[si]
        base = img["bg"] if img else bg * z
        arr = np.clip(base + g[..., None], 0, 255).astype(np.uint8)
        frame = Image.fromarray(arr).convert("RGBA")
        if img:
            draw_card(frame, img, lt, ends[si] - starts[si])
            draw_headline(frame, segs[si], lt, cy=1200, escala=0.72)
            draw_captions(frame, words, t, y=1480)
        else:
            frame.alpha_composite(rope_layer(t * 1.2))
            draw_headline(frame, segs[si], lt)
            draw_captions(frame, words, t)
        draw_chrome(frame, t, dur, script.get("tag", "MANHWA NEWS"))
        flash = max(0, 1 - lt / 0.12) * 0.55 if lt >= 0 else 0
        out = frame.convert("RGB")
        if shake:
            out = out.transform(out.size, Image.AFFINE, (1, 0, shake, 0, 1, shake * 0.5), fillcolor=(0, 0, 0))
        if flash > 0:
            out = Image.blend(out, Image.new("RGB", out.size, (255, 255, 255)), flash)
        ff.stdin.write(out.tobytes())
    ff.stdin.close()
    ff.wait()


def thumbnail(script, path, base_dir="."):
    seg = {"destaque": script["thumb"], "tamanho": 150}
    if script.get("thumb_sub"):
        seg["sub"] = script["thumb_sub"]
    if script.get("thumb_imagem"):
        img = prep_image(script["thumb_imagem"], base_dir, script.get("thumb_foco", 0.5))
        im = Image.fromarray(np.clip(img["bg"] * 1.3, 0, 255).astype(np.uint8)).convert("RGBA")
        draw_card(im, img, 10, 10)
        draw_headline(im, seg, 1, cy=1260, escala=0.85)
    else:
        bg, _ = base_layers()
        im = Image.fromarray(np.clip(bg * 1.4, 0, 255).astype(np.uint8)).convert("RGBA")
        im.alpha_composite(rope_layer(0))
        draw_headline(im, seg, 1)
    draw_chrome(im, 0, 1, script.get("tag", "MANHWA NEWS"))
    im.convert("RGB").save(path, quality=92)


def main():
    script = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    voice_mp3 = os.path.join(out, "narracao.mp3")
    words, starts = asyncio.run(narrate(script["segmentos"], script.get("voz", "pt-BR-AntonioNeural"),
                                        script.get("velocidade", "+12%"), voice_mp3))
    dur = duration(voice_mp3) + 1.2
    music = os.path.join(out, "trilha.wav")
    make_music(music, dur, starts[1:])
    mix = os.path.join(out, "audio_final.m4a")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", voice_mp3, "-i", music, "-filter_complex",
                    "[1:a]volume=0.22[m];[0:a]volume=1.6,apad[v];[v][m]amix=inputs=2:duration=longest:normalize=0,"
                    "loudnorm=I=-14:TP=-1.5[a]", "-map", "[a]", "-t", str(dur), "-c:a", "aac", "-b:a", "192k", mix],
                   check=True)
    json.dump({"palavras": words, "inicio_segmentos": starts}, open(os.path.join(out, "tempos.json"), "w"), ensure_ascii=False, indent=1)
    base_dir = os.path.dirname(os.path.abspath(sys.argv[1]))
    render(script, words, starts, dur, os.path.join(out, "short.mp4"), mix, base_dir)
    thumbnail(script, os.path.join(out, "thumbnail.jpg"), base_dir)
    with open(os.path.join(out, "post.txt"), "w", encoding="utf-8") as f:
        f.write(f"TÍTULO:\n{script['titulo']}\n\nDESCRIÇÃO:\n{script['descricao']}\n\nTAGS:\n{', '.join(script['tags'])}\n")
    print("ok", round(dur, 1), "s")


if __name__ == "__main__":
    main()
