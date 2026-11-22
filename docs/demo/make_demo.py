#!/usr/bin/env python3
"""Render docs/demo/demo.gif from docs/demo/session.json, the transcript of a
real `claude -p` run with this plugin (nothing in it is written by hand).

    python3 docs/demo/make_demo.py /path/to/chrome     # needs a Chromium binary and ffmpeg

Each frame is an HTML page showing the session up to one step, captured by
headless Chromium, so Arabic is shaped and ordered by a real text engine.
"""
import html
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "session.json"), encoding="utf-8"))
# a compound command the permission mode refused (Claude then retried it in simpler form) stays in
# session.json but is not drawn
S["steps"] = [st for st in S["steps"] if not (st["kind"] == "tool" and re.search(
    r"can't be checked before it runs|requires approval", st.get("result", "")))]
W, H = 1100, 900
ANSWER_BLOCKS = 4          # paragraphs of the final answer that fit in the frame (the rest is in session.json)
CSS = """
*{box-sizing:border-box} body{margin:0;background:#0f1419;color:#d6dbe1;font:17px/1.55 'DejaVu Sans Mono','Noto Sans Arabic',monospace;width:%dpx;height:%dpx;overflow:hidden}
.bar{background:#1c232b;padding:10px 18px;color:#8b98a5;font-size:14px;display:flex;gap:8px;align-items:center}
.dot{width:12px;height:12px;border-radius:50%%;display:inline-block}
.main{padding:18px 26px}
.prompt{color:#fff}.prompt b{color:#e8a33d}
.tool{margin-top:14px;color:#7fd1a0}.tool span{color:#8b98a5}
.res{margin:4px 0 0 22px;padding:6px 12px;border-left:2px solid #2c3640;color:#aab4be;font-family:'Noto Naskh Arabic','Noto Sans Arabic',serif;font-size:18px;line-height:1.7}
.ans{margin-top:16px;padding:14px 18px;background:#161d24;border-radius:8px;font-family:'DejaVu Sans','Noto Naskh Arabic',sans-serif;font-size:17px}
.ans b{color:#fff}.ans blockquote{margin:8px 0;padding:4px 14px;border-right:3px solid #e8a33d;color:#f0d9a8;font-size:19px}
.foot{position:absolute;bottom:10px;left:26px;right:26px;color:#5c6b7a;font-size:13px}
""" % (W, H)


def md(text: str) -> str:
    """The small subset of Markdown the answer uses."""
    out = []
    for line in text.split("\n"):
        e = html.escape(line)
        e = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", e)
        if line.startswith("&gt; ") or e.startswith("&gt; "):
            out.append(f"<blockquote dir='rtl'>{e[5:]}</blockquote>")
        elif e.startswith("- "):
            out.append(f"<div dir='auto'>• {e[2:]}</div>")
        elif e.strip():
            out.append(f"<div dir='auto'>{e}</div>")
    return "\n".join(out)


def first_lines(text: str, n: int) -> str:
    lines = [l for l in text.split("\n") if l.strip()][:n]
    return "<br>".join(html.escape(l[:118] + ("…" if len(l) > 118 else "")) for l in lines)


def page(upto: int, answer_chars: int | None) -> str:
    b = [f"<div class='prompt'><b>&gt;</b> {html.escape(S['prompt'])}</div>"]
    for i, st in enumerate(S["steps"][:upto]):
        if st["kind"] == "tool":
            cmd = re.sub(r"^python3 skills/[^/]+/scripts/", "", st["command"])
            b.append(f"<div class='tool'>● {html.escape(st['name'])} <span>{html.escape(cmd)}</span></div>")
            if st["name"] != "Skill":
                b.append(f"<div class='res' dir='rtl'>{first_lines(st['result'], 2)}</div>")
        elif st["text"] and i == len(S["steps"]) - 1:
            text = "\n\n".join(st["text"].split("\n\n")[:ANSWER_BLOCKS])   # the frame shows the start of the answer
            if answer_chars is not None:
                text = text[:answer_chars]
            b.append(f"<div class='ans'>{md(text)}</div>")
    foot = (f"Real session · {S['model']} · {S['turns']} turns, {S['seconds']} s · recorded {S['recorded_on']} · "
            "full transcript: docs/demo/session.json")
    return (f"<!doctype html><meta charset='utf-8'><style>{CSS}</style><div class='bar'>"
            "<i class='dot' style='background:#ff5f57'></i><i class='dot' style='background:#febc2e'></i>"
            "<i class='dot' style='background:#28c840'></i>&nbsp; claude — moroccan-law</div>"
            f"<div class='main'>{''.join(b)}</div><div class='foot'>{foot}</div>")


def main() -> None:
    chrome = sys.argv[1]
    n = len(S["steps"])
    answer = "\n\n".join(S["steps"][-1]["text"].split("\n\n")[:ANSWER_BLOCKS])
    frames = [(1, None, 1.6)] + [(k, None, 1.4) for k in range(2, n)]          # prompt, then each tool step
    cuts = [m.end() for m in re.finditer(r"\n\n", answer)] + [len(answer)]
    frames += [(n, c, 1.3) for c in cuts[:-1]] + [(n, cuts[-1], 7.0)]
    with tempfile.TemporaryDirectory() as tmp:
        lines = []
        for i, (upto, chars, secs) in enumerate(frames):
            hp, pp = os.path.join(tmp, f"f{i}.html"), os.path.join(tmp, f"f{i}.png")
            open(hp, "w", encoding="utf-8").write(page(upto, chars))
            subprocess.run([chrome, "--headless=new", "--no-sandbox", "--hide-scrollbars", f"--window-size={W},{H}",
                            f"--screenshot={pp}", "file://" + hp], check=True, capture_output=True)
            lines += [f"file '{pp}'", f"duration {secs}"]
        lines.append(lines[-2])
        lst = os.path.join(tmp, "list.txt")
        open(lst, "w").write("\n".join(lines) + "\n")
        out = os.path.join(HERE, "demo.gif")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-vf",
                        "split[a][b];[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=none", out], check=True)
        subprocess.run(["cp", os.path.join(tmp, f"f{len(frames) - 1}.png"), os.path.join(HERE, "demo.png")], check=True)
    print(out, os.path.getsize(out) // 1024, "KB,", len(frames), "frames")


if __name__ == "__main__":
    main()
