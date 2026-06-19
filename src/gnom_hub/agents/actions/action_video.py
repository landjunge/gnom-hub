# action_video.py — Video recording, merging, and editing for agent demos
# macOS: uses native `screencapture` (no Docker, no cloud)
# Cross-platform fallback: ffmpeg if available
import os
import re
import subprocess
import uuid


VIDEO_BLOCK = re.compile(
    r"rm\s+-rf\s+/.+|:\(\)\s*\{\s*:\|\:&\s*\}\;:",  # catastrophic patterns only
    re.I,
)


def _resolve_wd(wd):
    return os.path.abspath(wd) if wd else os.getcwd()


def _safe_video_path(wd, name):
    """Allow only writes inside the workspace."""
    base = os.path.abspath(wd)
    if not name:
        return None
    target = os.path.abspath(os.path.join(base, name))
    if not target.startswith(base + os.sep) and target != base:
        return None
    return target


def _has(cmd):
    """Check if a system command is available."""
    try:
        return subprocess.run(["which", cmd], capture_output=True, timeout=2).returncode == 0
    except Exception:
        return False


def _parse_video_opts(raw):
    """Parse 'key=value|key=value' into a dict."""
    out = {}
    for part in raw.split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip().lower()] = v.strip()
        else:
            out.setdefault("input", part.strip())
    return out


def handle_screen_record(ans, ms, agent, perms, wd):
    """
    [VIDEO:SCREEN:filename=out.mov|duration=20|audio=on|fps=30|region=0,0,1920,1080]
    Captures the screen for `duration` seconds. macOS uses screencapture, others ffmpeg.
    """
    for m in ms:
        raw = m.group(1).strip()
        opts = _parse_video_opts(raw)
        if "run" not in perms and "video" not in perms:
            ans = ans.replace(m.group(0), f"[System: {agent.get('name','?')} hat keine VIDEO-Berechtigung.]")
            continue

        duration = int(opts.get("duration", 15))
        filename = opts.get("filename") or f"recording_{uuid.uuid4().hex[:8]}.mov"
        # 'tts' = TTS-Audio (`say` vorher, dann mit ffmpeg mixen).
        # KEIN Mikrofon — TTS läuft über `say -o` und erzeugt eine AIFF-Datei.
        tts_text = opts.get("tts", "").strip()
        fps = int(opts.get("fps", 30))
        region = opts.get("region", "")

        out_path = _safe_video_path(_resolve_wd(wd), filename)
        if not out_path:
            ans = ans.replace(m.group(0), f"[Video-Fehler: Pfad '{filename}' außerhalb des Workspace.]")
            continue

        # ── Berechtigungs-Check VOR dem Recording (macOS) ──
        # Screen Recording braucht explizite Erlaubnis in
        # System Settings → Privacy & Security → Screen Recording.
        # Beim ERSTEN Aufruf poppt macOS einen Dialog auf — der User
        # muss bestätigen. Wir posten SOFORT die Anleitung, damit der
        # User den Dialog bewusst bestätigen kann.
        if _has("screencapture"):
            try:
                from gnom_hub.db import add_chat_message, get_active_project
                add_chat_message(
                    get_active_project(),
                    "WatchdogAG", "watchdogag", "chat",
                    "🛡️ @user: macOS fragt JETZT nach 'Screen Recording'-Berechtigung. "
                    "Klicke im Dialog auf 'Erlauben' (Open System Settings → Privacy & Security → "
                    "Screen Recording → Terminal.app aktivieren falls nicht automatisch). "
                    "Anschließend: [VIDEO:SCREEN:filename=gnom_demo.mov|duration=15] nochmal senden.",
                )
            except Exception:
                pass
            # Probe-Test
            try:
                probe = subprocess.run(
                    ["screencapture", "-x", "-C", "-t", "png", "/tmp/_sc_probe.png"],
                    capture_output=True, text=True, timeout=3,
                )
                probe_ok = (probe.returncode == 0
                            and os.path.exists("/tmp/_sc_probe.png")
                            and os.path.getsize("/tmp/_sc_probe.png") > 100)
            except Exception:
                probe_ok = False
            try: os.remove("/tmp/_sc_probe.png")
            except OSError: pass
            if not probe_ok:
                ans = ans.replace(
                    m.group(0),
                    f"[System: Screen-Recording fehlgeschlagen. @user: Erlaube Screen Recording "
                    f"in System Settings → Privacy & Security → Screen Recording "
                    f"(Terminal.app + Python). Dann: [VIDEO:SCREEN:filename={filename}|duration={duration}] nochmal.]"
                )
                continue

        # ── TTS-Audio (NICHT Mikrofon!) ──
        # Wenn tts=... angegeben ist, erzeugt `say` eine AIFF-Datei,
        # die ffmpeg danach mit dem Screen-Recording mixt.
        tts_audio_path = None
        if tts_text and _has("say") and _has("ffmpeg"):
            tts_audio_path = out_path + ".tts.aiff"
            try:
                subprocess.run(
                    ["say", "-v", "Anna", "-o", tts_audio_path, tts_text],
                    check=True, capture_output=True, timeout=20,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                ans = ans.replace(
                    m.group(0,
                    f"[System: TTS fehlgeschlagen — {str(e)[:100]}. "
                    f"Aufnahme wird ohne Audio gemacht."
                    )
                )
                tts_audio_path = None

        try:
            if _has("screencapture") and not region:
                # macOS native screen capture
                if tts_audio_path and _has("ffmpeg"):
                    # TTS-Audio ins Video mixen
                    tmp = out_path + ".video.mov"
                    cmd = ["screencapture", "-V", str(duration), "-r", str(fps), "-o", tmp]
                    subprocess.run(cmd, check=True, capture_output=True, timeout=duration + 10)
                    # TTS-Audio ist oft kürzer als duration → mit `-shortest` arbeiten
                    audio_cmd = [
                        "ffmpeg", "-y",
                        "-i", tmp, "-i", tts_audio_path,
                        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                        "-c:a", "aac", "-shortest", out_path,
                    ]
                    subprocess.run(audio_cmd, check=True, capture_output=True, timeout=duration + 15)
                    try:
                        os.remove(tmp)
                        os.remove(tts_audio_path)
                    except OSError:
                        pass
                else:
                    cmd = ["screencapture", "-V", str(duration), "-r", str(fps), "-o", out_path]
                    subprocess.run(cmd, check=True, capture_output=True, timeout=duration + 10)
            elif _has("ffmpeg"):
                # Linux/cross-platform fallback
                if region:
                    x, y, w, h = region.split(",")
                    region_arg = f"{w}x{h}+{x}+{y}"
                    input_arg = f":0.0+{x},{y}"
                else:
                    region_arg, input_arg = "", ":0.0"
                cmd = [
                    "ffmpeg", "-y", "-f", "x11grab", "-framerate", str(fps),
                    "-video_size", region_arg or "1920x1080", "-i", input_arg,
                    "-t", str(duration), out_path,
                ]
                if tts_audio_path:
                    # TTS-Audio mit Video mischen
                    cmd = [
                        "ffmpeg", "-y", "-f", "x11grab", "-framerate", str(fps),
                        "-video_size", region_arg or "1920x1080", "-i", input_arg,
                        "-i", tts_audio_path,
                        "-t", str(duration),
                        "-c:v", "libx264", "-preset", "fast",
                        "-c:a", "aac", "-shortest", out_path,
                    ]
                else:
                    cmd += ["-c:v", "libx264", "-preset", "fast"]
                subprocess.run(cmd, check=True, capture_output=True, timeout=duration + 15)
            else:
                ans = ans.replace(m.group(0), "[Video-Fehler: weder `screencapture` (macOS) noch `ffmpeg` installiert.]")
                continue

            ans = ans.replace(
                m.group(0),
                f"[System: Screen-Recording '{os.path.basename(out_path)}' aufgenommen ({duration}s, {fps}fps) → {out_path}]"
            )
        except subprocess.CalledProcessError as e:
            err = e.stderr.decode("utf-8", errors="ignore")[:300] if e.stderr else str(e)
            ans = ans.replace(m.group(0), f"[Video-Fehler: screencapture/ffmpeg fehlgeschlagen: {err}]")
        except subprocess.TimeoutExpired:
            ans = ans.replace(m.group(0), f"[Video-Fehler: Timeout bei Aufnahme (> {duration+10}s)]")
        except Exception as e:
            ans = ans.replace(m.group(0), f"[Video-Fehler: {str(e)[:200]}]")
    return ans


def handle_video_merge(ans, ms, agent, perms, wd):
    """
    [VIDEO:MERGE:input1.mov,input2.mp4|output=final.mp4]
    Concatenates two or more video files. Requires ffmpeg.
    """
    for m in ms:
        raw = m.group(1).strip()
        opts = _parse_video_opts(raw)
        if "run" not in perms and "video" not in perms:
            ans = ans.replace(m.group(0), f"[System: {agent.get('name','?')} hat keine VIDEO-Berechtigung.]")
            continue

        inputs_raw = opts.get("input", opts.get("inputs", ""))
        inputs = [i.strip() for i in re.split(r"[,|]", inputs_raw) if i.strip()]
        output = opts.get("output", "merged.mp4")

        if len(inputs) < 2:
            ans = ans.replace(m.group(0), "[Video-Fehler: MERGE braucht mindestens 2 Eingabedateien (input1,input2).]")
            continue
        if not _has("ffmpeg"):
            ans = ans.replace(m.group(0), "[Video-Fehler: ffmpeg nicht installiert. Installiere via: brew install ffmpeg]")
            continue

        wd_abs = _resolve_wd(wd)
        resolved = []
        for inp in inputs:
            p = _safe_video_path(wd_abs, inp)
            if not p or not os.path.exists(p):
                ans = ans.replace(m.group(0), f"[Video-Fehler: Eingabedatei nicht gefunden: {inp}]")
                break
            resolved.append(p)
        else:
            out_path = _safe_video_path(wd_abs, output)
            if not out_path:
                ans = ans.replace(m.group(0), f"[Video-Fehler: Output-Pfad '{output}' außerhalb des Workspace.]")
                continue

            list_file = out_path + ".concat.txt"
            try:
                with open(list_file, "w") as f:
                    for p in resolved:
                        f.write(f"file '{p}'\n")
                cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", out_path]
                subprocess.run(cmd, check=True, capture_output=True, timeout=120)
                ans = ans.replace(
                    m.group(0),
                    f"[System: Videos zusammengeführt → {out_path} ({len(resolved)} Dateien)]"
                )
            except subprocess.CalledProcessError as e:
                err = e.stderr.decode("utf-8", errors="ignore")[:300] if e.stderr else str(e)
                ans = ans.replace(m.group(0), f"[Video-Fehler: ffmpeg concat fehlgeschlagen: {err}]")
            except Exception as e:
                ans = ans.replace(m.group(0), f"[Video-Fehler: {str(e)[:200]}]")
            finally:
                try:
                    os.remove(list_file)
                except OSError:
                    pass
    return ans


def handle_video_edit(ans, ms, agent, perms, wd):
    """
    [VIDEO:EDIT:input.mov|output=cut.mp4|start=00:00:05|end=00:00:15|scale=1280x720]
    Cuts, scales, or trims a video. Requires ffmpeg.
    """
    for m in ms:
        raw = m.group(1).strip()
        opts = _parse_video_opts(raw)
        if "run" not in perms and "video" not in perms:
            ans = ans.replace(m.group(0), f"[System: {agent.get('name','?')} hat keine VIDEO-Berechtigung.]")
            continue

        input_file = opts.get("input", "")
        output = opts.get("output", "edited.mp4")
        start = opts.get("start", "")
        end = opts.get("end", "")
        scale = opts.get("scale", "")

        if not _has("ffmpeg"):
            ans = ans.replace(m.group(0), "[Video-Fehler: ffmpeg nicht installiert. Installiere via: brew install ffmpeg]")
            continue

        wd_abs = _resolve_wd(wd)
        in_path = _safe_video_path(wd_abs, input_file)
        out_path = _safe_video_path(wd_abs, output)
        if not in_path or not os.path.exists(in_path):
            ans = ans.replace(m.group(0), f"[Video-Fehler: Eingabedatei nicht gefunden: {input_file}]")
            continue
        if not out_path:
            ans = ans.replace(m.group(0), f"[Video-Fehler: Output-Pfad '{output}' außerhalb des Workspace.]")
            continue

        cmd = ["ffmpeg", "-y", "-i", in_path]
        if start:
            cmd += ["-ss", start]
        if end:
            cmd += ["-to", end]
        vf = []
        if scale:
            vf.append(f"scale={scale}")
        if vf:
            cmd += ["-vf", ",".join(vf)]
        cmd += ["-c:a", "copy", out_path]

        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
            ops = []
            if start:
                ops.append(f"start={start}")
            if end:
                ops.append(f"end={end}")
            if scale:
                ops.append(f"scale={scale}")
            ans = ans.replace(
                m.group(0),
                f"[System: Video geschnitten → {out_path} ({', '.join(ops) or 'kein Schnitt'})]"
            )
        except subprocess.CalledProcessError as e:
            err = e.stderr.decode("utf-8", errors="ignore")[:300] if e.stderr else str(e)
            ans = ans.replace(m.group(0), f"[Video-Fehler: ffmpeg edit fehlgeschlagen: {err}]")
        except Exception as e:
            ans = ans.replace(m.group(0), f"[Video-Fehler: {str(e)[:200]}]")
    return ans
