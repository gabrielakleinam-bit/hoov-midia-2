#!/usr/bin/env python3
"""Padroniza a exportação de um Reel Hoov: 1080x1920, 30 fps, H.264, AAC estéreo 48 kHz,
volume -14 LUFS (medido nos Reels publicados: de -16,5 a -13,6, sem padrão fixo).
Uso: python3 finalize_reel.py entrada.mp4 saida.mp4"""
import subprocess, sys, json
src, dst = sys.argv[1:3]
probe = json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-of","json",src]))
has_a = any(s["codec_type"]=="audio" for s in probe["streams"])
cmd = ["ffmpeg","-v","error","-y","-i",src,
       "-vf","scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=#161616,fps=30,format=yuv420p",
       "-c:v","libx264","-preset","veryfast","-crf","20","-movflags","+faststart"]
if has_a:
    cmd += ["-af","loudnorm=I=-14:TP=-1.5:LRA=11","-c:a","aac","-b:a","192k","-ar","48000","-ac","2"]
else:
    cmd += ["-an"]
subprocess.check_call(cmd+[dst]); print("ok", dst)
