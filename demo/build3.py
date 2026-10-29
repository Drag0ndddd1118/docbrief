import json, subprocess, os, re
from PIL import Image, ImageDraw, ImageFont
B = "build"; FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def dur(f): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f]).decode())
TEXT = dict(re.findall(r'\("(s\w+)",\s*"((?:[^"\\]|\\.)*)"\)', open("narration3.py").read()))
M = json.load(open(f"{B}/marks3.json")); OFF = 1.2
m = lambda k, dt=0: round(M[k] - OFF + dt, 2)
RAW = f"{B}/raw3.webm"
PAD = 0.45
# ---- end card ------------------------------------------------------------
img = Image.new("RGB", (1920, 1080), (11, 14, 20)); d = ImageDraw.Draw(img)
def txt(y, s, size, fill, bold=True):
    f = ImageFont.truetype(FONT, size); w = d.textlength(s, font=f); d.text(((1920 - w) / 2, y), s, font=f, fill=fill)
d.rectangle([0, 0, 1920, 14], fill=(118, 185, 0))
txt(210, "DocBrief", 170, (255, 255, 255))
txt(430, "AI that cites, verifies, and fact-checks", 58, (118, 185, 0))
txt(540, "Ask any 10-K. Get the page.", 56, (255, 255, 255))
txt(680, "github.com/Drag0ndddd1118/docbrief", 56, (255, 255, 255))
txt(770, "Open source · MIT license · Python + Streamlit", 38, (170, 180, 195))
txt(860, "NVIDIA Nemotron (Nano · Super · Ultra)  ×  Nebius Token Factory  ×  Tavily", 40, (255, 255, 255))
img.save(f"{B}/endcard.png")
# ---- scenes: (id, [segments], opts) --------------------------------------
# segment: ("v", start, end, speed) from raw video | ("img", path)
scenes = [
 ("s0", [("v", m("ans1", -0.5), m("ans1", 10.1), 1)], {"label": (0.2, 5.5, "Real NVIDIA FY2026 10-K · every answer cites its page")}),
 ("s1", [("v", m("home", -0.8), m("home", 0.1), 1)], {}),
 ("s2", [("v", m("home_cards", 0.0), m("home_cards", 0.3), 1)], {"box": (36, 350, 345, 160)}),
 ("s3", [("v", m("click_show", -0.2), m("metrics", -0.2), 1)], {}),
 ("s4", [("v", m("metrics", -0.2), m("metrics_end"), 1)], {}),
 ("s5", [("v", m("fc_cached", -0.2), m("fc_cached_end"), 0.45)], {}),
 ("s6", [("v", m("fc_click", -0.5), m("fc_running"), 6), ("v", m("fc_live_done", -0.3), m("fc_live_end"), 0.8)], {"label": (0.2, 4.2, "Live: Nano picks claims → Tavily web search → Super reconciles (wait sped up 6×)")}),
 ("s7", [("v", m("q2_typed", -3.6), m("q2_sent"), 1), ("v", m("q2_sent"), m("q2_answer", -0.5), 4), ("v", m("q2_answer", -0.3), m("q2_read"), 1)], {"label": (3.7, 6.2, "Live Nemotron Super call (wait sped up 4×)")}),
 ("s8", [("v", m("q3_typed", -3.4), m("q3_typed"), 2), ("v", m("q3_typed"), m("q3_typed", 3.5), 1)], {}),
 ("s9", [("v", m("q3_read", 0.3), m("meter"), 1)], {}),
 ("s10", [("img", "build/endcard.png")], {}),
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
            subprocess.run(["ffmpeg","-v","error","-y","-i",RAW,"-vf",vf,"-an","-c:v","libx264","-crf","17","-pix_fmt","yuv420p",out],check=True)
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
subprocess.run(["ffmpeg","-v","error","-y","-i",f"{B}/video_nosound.mp4","-i",f"{B}/narration.wav","-vf",f"ass={B}/cap.ass","-c:v","libx264","-crf","18","-preset","medium","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart","docbrief_demo_v3.mp4"],check=True)
print("FINAL", dur("docbrief_demo_v3.mp4"))
