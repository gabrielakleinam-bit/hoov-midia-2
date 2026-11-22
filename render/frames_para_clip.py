#!/usr/bin/env python3
"""Monta o clipe da gravação (frames + timestamps) em MP4 30 fps. Uso: frames_para_clip.py fr meta.json rec.mp4"""
import json, sys, subprocess, pathlib
fr, meta, out = sys.argv[1:4]
ts = json.load(open(meta))["ts"]; n = len(ts)
lst = pathlib.Path(out).with_suffix(".txt")
with open(lst, "w") as f:
    for i in range(n):
        d = (ts[i + 1] - ts[i]) if i + 1 < n else 0.1
        f.write(f"file '{pathlib.Path(fr).resolve()}/{i:05d}.jpg'\nduration {max(d, 0.005):.4f}\n")
    f.write(f"file '{pathlib.Path(fr).resolve()}/{n-1:05d}.jpg'\n")
subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",str(lst),"-vf","fps=30,scale=1080:1920,format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","18",out],check=True)
print("ok", out)
