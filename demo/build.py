import json, subprocess, os, re
from PIL import Image, ImageDraw, ImageFont
B = "build"; FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def dur(f): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f]).decode())
TEXT = dict(re.findall(r'\("(s\w+)",\s*"((?:[^"\\]|\\.)*)"\)', open("narration.py").read()))
M = json.load(open(f"{B}/marks.json"))
PAD = 0.45
# ---- end card ------------------------------------------------------------
img = Image.new("RGB", (1920, 1080), (11, 14, 20)); d = ImageDraw.Draw(img)
def txt(y, s, size, fill, bold=True):
    f = ImageFont.truetype(FONT, size); w = d.textlength(s, font=f); d.text(((1920 - w) / 2, y), s, font=f, fill=fill)
d.rectangle([0, 0, 1920, 14], fill=(118, 185, 0))
txt(250, "📑" if False else "DocBrief", 170, (255, 255, 255))
txt(450, "Speed-read papers & annual reports — with receipts", 52, (118, 185, 0))
txt(580, "github.com/Drag0ndddd1118/docbrief", 60, (255, 255, 255))
txt(700, "Open source · MIT license · Python + Streamlit", 40, (170, 180, 195))
txt(800, "Built on NVIDIA Nemotron  ×  Nebius Token Factory  ×  Tavily", 46, (255, 255, 255))
img.save(f"{B}/endcard.png")
# ---- scenes: (id, [segments], opts) --------------------------------------
# segment: ("v", start, end, speed) from raw video | ("img", path)
scenes = [
 ("s0", [("v", 102.2, 107.6, 1)], {}),
 ("s1", [("v", 3.6, 5.2, 1)], {"freeze": True}),
 ("s2", [("v", 3.6, 5.2, 1)], {"freeze": True, "box": (28, 250, 336, 262)}),
 ("s3", [("v", 6.0, 25.2, 4), ("v", 25.5, 30.5, 1)], {"label": (0, 4.7, "Live Nemotron call — thinking time sped up 4×")}),
 ("s4", [("v", 26.8, 30.0, 1), ("v", 31.9, 36.1, 1)], {}),
 ("s5", [("v", 36.4, 45.8, 1)], {"freeze": True}),
 ("sT", [("v", 47.5, 48.4, 0.12), ("v", 48.5, 79.5, 4), ("v", 80.0, 91.4, 1)], {"label": (7.7, 15.3, "Live Nano → Tavily web search → Super — wait sped up 4×")}),
 ("s6", [("v", 97.0, 107.6, 1)], {"freeze": True}),
 ("s7", [("v", 108.0, 112.3, 1)], {"freeze": True}),
 ("s8", [("v", 113.9, 116.6, 1), ("v", 128.0, 135.5, 1)], {"freeze": True}),
 ("s9", [("v", 136.2, 139.6, 1), ("img", "build/endcard.png")], {"endcard": True}),
]
starts, t = {}, 0.0
clips = []
for sid, segs, o in scenes:
    ad = dur(f"{B}/{sid}.mp3"); L = ad + PAD; starts[sid] = (t, ad)
    parts = []
    for k, sg in enumerate(segs):
        out = f"{B}/{sid}_{k}.mp4"
        if sg[0] == "v":
            _, a, b, sp = sg
            vf = f"trim=start={a}:end={b},setpts=(PTS-STARTPTS)/{sp},fps=25,scale=1920:1080:flags=lanczos"
            if o.get("box") and k == 0:
                x, y, w, h = o["box"]; vf += f",drawbox=x={x}:y={y}:w={w}:h={h}:color=0x76b900@0.95:t=5"
            subprocess.run(["ffmpeg","-v","error","-y","-i",f"{B}/raw.webm","-vf",vf,"-an","-c:v","libx264","-crf","17","-pix_fmt","yuv420p",out],check=True)
        else:
            subprocess.run(["ffmpeg","-v","error","-y","-loop","1","-framerate","25","-t","30","-i",sg[1],"-vf","scale=1920:1080,fps=25","-an","-c:v","libx264","-crf","17","-pix_fmt","yuv420p",out],check=True)
        parts.append(out)
    # concat parts, then pad/trim to L
    lst = f"{B}/{sid}_list.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in parts))
    joined = f"{B}/{sid}_joined.mp4"
    subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",lst,"-c","copy",joined],check=True)
    cur = dur(joined)
    final = f"{B}/{sid}_clip.mp4"
    if o.get("endcard"):
        # real clip first (deep toggle), then end card fills the rest of the narration
        vid_len = dur(parts[0]); card_len = max(L - vid_len, 3)
        subprocess.run(["ffmpeg","-v","error","-y","-i",parts[0],"-i",parts[1],"-filter_complex",
                        f"[1:v]trim=duration={card_len},setpts=PTS-STARTPTS[c];[0:v][c]concat=n=2:v=1:a=0,trim=duration={L}[v]","-map","[v]","-c:v","libx264","-crf","17","-pix_fmt","yuv420p",final],check=True)
    else:
        pad = max(0, L - cur)
        subprocess.run(["ffmpeg","-v","error","-y","-i",joined,"-vf",f"tpad=stop_mode=clone:stop_duration={pad:.3f},trim=duration={L:.3f}","-c:v","libx264","-crf","17","-pix_fmt","yuv420p",final],check=True)
    print(sid, "audio", round(ad, 2), "clip", round(dur(final), 2), "src", round(cur, 2))
    clips.append(final); t += L
open(f"{B}/all.txt", "w").write("".join(f"file '{os.path.abspath(c)}'\n" for c in clips))
ins=[]; [ins.extend(["-i",c]) for c in clips]
subprocess.run(["ffmpeg","-v","error","-y",*ins,"-filter_complex","".join(f"[{i}:v]setpts=PTS-STARTPTS[v{i}];" for i in range(len(clips)))+"".join(f"[v{i}]" for i in range(len(clips)))+f"concat=n={len(clips)}:v=1:a=0[v]","-map","[v]","-r","25","-c:v","libx264","-crf","17","-pix_fmt","yuv420p",f"{B}/video_nosound.mp4"],check=True)
# ---- audio ----------------------------------------------------------------
for sid, _, _ in scenes:
    subprocess.run(["ffmpeg","-v","error","-y","-i",f"{B}/{sid}.mp3","-af",f"apad=pad_dur={PAD}","-ar","44100","-ac","2",f"{B}/{sid}.wav"],check=True)
open(f"{B}/aud.txt", "w").write("".join(f"file '{os.path.abspath(B)}/{sid}.wav'\n" for sid, _, _ in scenes))
subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",f"{B}/aud.txt","-c","copy",f"{B}/narration.wav"],check=True)
# ---- captions (ASS) ---------------------------------------------------------
def ts(x): h=int(x//3600); m=int(x%3600//60); s=x%60; return f"{h}:{m:02d}:{s:05.2f}"
ev = []
for sid, _, o in scenes:
    t0, ad = starts[sid]; w0 = json.load(open(f"{B}/{sid}.json"))["words"]
    w = []
    for x in w0:
        ps = x["w"].split()
        for j, p in enumerate(ps): w.append({"t": x["t"] + x["d"] * j / len(ps), "d": x["d"] / len(ps), "w": p})
    tok = TEXT[sid].split()
    if len(tok) == len(w):
        for x, tk in zip(w, tok): x["w"] = tk
    else: print("token mismatch", sid, len(tok), len(w))
    chunks, cur = [], []
    for i, x in enumerate(w):
        cur.append(x)
        end = x["w"][-1:] in ".?!,;:" and len(cur) >= 3
        if len(cur) >= 9 or end or i == len(w) - 1:
            chunks.append(cur); cur = []
    for c in chunks:
        s0 = t0 + c[0]["t"]; e = t0 + c[-1]["t"] + c[-1]["d"] + 0.15
        ev.append(f"Dialogue: 0,{ts(s0)},{ts(e)},Cap,,0,0,0,,{' '.join(x['w'] for x in c)}")
    if o.get("label"):
        a, b, s = o["label"]; ev.append(f"Dialogue: 1,{ts(t0+a)},{ts(t0+b)},Tag,,0,0,0,,{s}")
t1, _ = starts["s1"]
ev.append(f"Dialogue: 1,{ts(t1+0.3)},{ts(t1+11.5)},Big,,0,0,0,,{{\\pos(1100,500)\\an5}}Speed-read papers\\Nand annual reports.\\N{{\\c&H00B976&}}With receipts.")
hdr = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Cap,DejaVu Sans,50,&H00FFFFFF,&H000000FF,&HD0000000,&H80000000,-1,0,0,0,100,100,0,0,3,3,0,2,120,120,48,1
Style: Tag,DejaVu Sans,34,&H0000E0FF,&H000000FF,&HD0000000,&H80000000,-1,0,0,0,100,100,0,0,3,2,0,8,60,60,70,1
Style: Big,DejaVu Sans,86,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,5,60,60,60,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
open(f"{B}/cap.ass", "w").write(hdr + "\n".join(ev) + "\n")
subprocess.run(["ffmpeg","-v","error","-y","-i",f"{B}/video_nosound.mp4","-i",f"{B}/narration.wav","-vf",f"ass={B}/cap.ass","-c:v","libx264","-crf","18","-preset","medium","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart","docbrief_demo_v2.mp4"],check=True)
print("FINAL", dur("docbrief_demo_v2.mp4"))
