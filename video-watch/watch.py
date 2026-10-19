#!/usr/bin/env python3
"""Video watcher (runs on GitHub Actions). Fetch any video link, keep its native fps, pick scene frames + per-second
keyframes, transcribe with word timestamps, label speakers, and stream partial results to the HF dataset while it runs.
Live folder:  Saidie000/tab-render-out  live/<req>/   (status.json, partial.md, partial.json, contact_sheet.jpg, meta.json)
Final folder: Saidie000/tab-render-out  runs/<run_id>/ (everything in OUT, minus the source video)"""
import os, sys, json, time, re, math, subprocess, shutil, tarfile, zipfile, threading, traceback, urllib.request
T0 = time.time()
JOB = json.load(open(os.environ['VW_JOB'])) if os.environ.get('VW_JOB') else {}
URL = (JOB.get('url') or os.environ.get('VW_URL', '')).strip(); REQ = JOB.get('req') or os.environ.get('VW_REQ', 'manual'); RUN_ID = os.environ.get('RUN_ID', 'local')
if not re.match(r'^https?://\S+$', URL): sys.exit('bad url: %r' % URL)
if not re.match(r'^[\w.-]+$', REQ): sys.exit('bad req')
OPTS = dict(kv.split('=', 1) for kv in (JOB.get('opts') or os.environ.get('VW_OPTS', '')).split() if '=' in kv)
HF = os.environ.get('HF_TOKEN', ''); DS = 'Saidie000/tab-render-out'
W = os.path.abspath('work'); OUT = os.path.abspath('out'); MODELS = os.path.expanduser('~/.cache/vw-models')
for d in (W, OUT, MODELS): os.makedirs(d, exist_ok=True)
meta = {'url': URL, 'req': REQ, 'run_id': RUN_ID, 'opts': OPTS, 'errors': [], 'fetch_attempts': [], 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
status = {'stage': 'starting', 'run_id': RUN_ID, 'elapsed_s': 0}
def log(*a): print(f'[{time.time()-T0:6.1f}s]', *a, flush=True)
def sh(cmd, timeout=1800, check=False):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode: raise RuntimeError(f'{cmd[0]} exit {p.returncode}: {(p.stderr or p.stdout)[-800:]}')
    return p
def ts(t, ms=False):
    t = max(0.0, float(t)); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    if ms: return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s-int(s))*1000)) % 1000:03d}'
    return f'{h:02d}:{m:02d}:{s:05.2f}' if h else f'{m:02d}:{s:05.2f}'

# ---------------- live publishing ----------------
api = None
if HF:
    from huggingface_hub import HfApi, CommitOperationAdd
    api = HfApi(token=HF)
_live_lock = threading.Lock()
def live(files=None, **st):
    """write status.json (+ given local files) into live/<req>/ in one commit; never fatal"""
    status.update(st); status['elapsed_s'] = round(time.time() - T0, 1); status['updated_utc'] = time.strftime('%H:%M:%SZ', time.gmtime())
    log('LIVE', json.dumps({k: v for k, v in status.items() if k != 'partial_tail'})[:300])
    if not api: return
    ops = [CommitOperationAdd(path_in_repo=f'live/{REQ}/status.json', path_or_fileobj=json.dumps(status, indent=1).encode())]
    for f in files or []:
        if os.path.exists(f): ops.append(CommitOperationAdd(path_in_repo=f'live/{REQ}/{os.path.basename(f)}', path_or_fileobj=f))
    with _live_lock:
        for k in range(3):
            try: api.create_commit(repo_id=DS, repo_type='dataset', operations=ops, commit_message=f'live {REQ} {status["stage"]}'); return
            except Exception as e: log('live upload failed', type(e).__name__, str(e)[:200]); time.sleep(4 * (k + 1))

# ---------------- fetch ----------------
PROXY = ['--proxy', os.environ['VW_PROXY']] if os.environ.get('VW_PROXY') else []       # optional repo secret: a residential proxy
COOKIES = []
if os.environ.get('YT_COOKIES'):                                                         # optional repo secret: Netscape cookies.txt text
    open(os.path.join(W, 'cookies.txt'), 'w').write(os.environ['YT_COOKIES']); COOKIES = ['--cookies', os.path.join(W, 'cookies.txt')]
meta['fetch_extras'] = {'proxy': bool(PROXY), 'cookies': bool(COOKIES)}
def is_yt(u): return bool(re.search(r'(youtube\.com|youtu\.be)/', u))
def ytdlp(extra, label, timeout=900):
    for f in os.listdir(W):
        if f.startswith('src.'): os.remove(os.path.join(W, f))
    cmd = ['yt-dlp', '--no-playlist', '--no-progress', '--newline', '-S', 'res:1080,fps', '-f', 'bv*+ba/b',
           '--merge-output-format', 'mp4', '--write-info-json', '-o', f'{W}/src.%(ext)s'] + PROXY + COOKIES + extra + [URL]
    t = time.time(); p = sh(cmd, timeout=timeout)
    vids = [f for f in os.listdir(W) if f.startswith('src.') and not f.endswith(('.json', '.part', '.ytdl'))]
    err = '\n'.join(l for l in (p.stderr or '').splitlines() if 'ERROR' in l or 'WARNING' in l)[-1200:]
    ok = p.returncode == 0 and bool(vids)
    meta['fetch_attempts'].append({'route': label, 'ok': ok, 'seconds': round(time.time() - t, 1), 'error': None if ok else (err or (p.stderr or p.stdout)[-600:])})
    log('fetch', label, 'OK' if ok else 'FAIL', '' if ok else err[-300:])
    return os.path.join(W, vids[0]) if ok else None
def start_pot_server():
    try:
        sh(['docker', 'run', '--name', 'bgutil', '-d', '-p', '4416:4416', '--init', 'brainicism/bgutil-ytdlp-pot-provider'], timeout=240, check=True)
        for _ in range(30):
            try: urllib.request.urlopen('http://127.0.0.1:4416/ping', timeout=3); return True
            except Exception: time.sleep(2)
    except Exception as e:
        meta['fetch_attempts'].append({'route': 'pot-server-start', 'ok': False, 'error': str(e)[-400:]})
    return False
def invidious():
    vid = re.search(r'(?:v=|youtu\.be/|shorts/)([\w-]{11})', URL)
    if not vid: return None
    vid = vid.group(1)
    for inst in ('https://inv.nadeko.net', 'https://yewtu.be', 'https://invidious.nerdvpn.de', 'https://iv.ggtyler.dev'):
        label = f'invidious {inst}'
        try:
            j = json.loads(urllib.request.urlopen(urllib.request.Request(f'{inst}/api/v1/videos/{vid}', headers={'User-Agent': 'Mozilla/5.0'}), timeout=20).read())
            streams = sorted([s for s in j.get('formatStreams', []) if s.get('url')], key=lambda s: int((s.get('resolution') or '0p')[:-1] or 0))
            if not streams: raise RuntimeError('no muxed streams in API answer')
            dst = os.path.join(W, 'src.mp4'); t = time.time()
            with urllib.request.urlopen(urllib.request.Request(streams[-1]['url'], headers={'User-Agent': 'Mozilla/5.0'}), timeout=300) as r, open(dst, 'wb') as f: shutil.copyfileobj(r, f)
            if os.path.getsize(dst) < 50000: raise RuntimeError(f'download too small ({os.path.getsize(dst)} bytes)')
            meta['fetch_attempts'].append({'route': label, 'ok': True, 'seconds': round(time.time() - t, 1), 'error': None})
            json.dump({'title': j.get('title'), 'uploader': j.get('author'), 'duration': j.get('lengthSeconds'), 'webpage_url': URL, 'via': inst}, open(os.path.join(W, 'src.info.json'), 'w'))
            return dst
        except Exception as e:
            meta['fetch_attempts'].append({'route': label, 'ok': False, 'error': f'{type(e).__name__}: {str(e)[:300]}'}); log('fetch', label, 'FAIL', str(e)[:200])
    return None
def fetch():
    live(stage='fetching')
    src = ytdlp([], 'yt-dlp default')
    if src or not is_yt(URL): return src
    for pc in ('tv_simply', 'web_safari', 'mweb', 'android_vr', 'ios', 'tv'):
        src = ytdlp(['--extractor-args', f'youtube:player_client={pc}'], f'yt-dlp player_client={pc}')
        if src: return src
    if start_pot_server():
        for pc in ('mweb', 'web', 'web_safari'):
            src = ytdlp(['--extractor-args', f'youtube:player_client={pc}'], f'yt-dlp + PO-token server, player_client={pc}')
            if src: return src
    return invidious()

# ---------------- frames ----------------
def probe(src):
    j = json.loads(sh(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', src], check=True).stdout)
    v = next((s for s in j['streams'] if s['codec_type'] == 'video'), {}); a = next((s for s in j['streams'] if s['codec_type'] == 'audio'), None)
    def fr(x):
        try: n, d = x.split('/'); return round(float(n) / float(d), 3) if float(d) else None
        except Exception: return None
    return {'duration': float(j['format'].get('duration') or v.get('duration') or 0), 'width': v.get('width'), 'height': v.get('height'),
            'fps_avg': fr(v.get('avg_frame_rate', '0/0')), 'fps_r': fr(v.get('r_frame_rate', '0/0')), 'vcodec': v.get('codec_name'),
            'nb_frames': int(v['nb_frames']) if str(v.get('nb_frames', '')).isdigit() else None, 'has_audio': a is not None,
            'acodec': a.get('codec_name') if a else None, 'size_mb': round(os.path.getsize(src) / 1e6, 2)}
def frames(src, dur):
    from PIL import Image, ImageDraw, ImageFont
    kf = os.path.join(W, 'kf'); sc = os.path.join(W, 'sc'); os.makedirs(kf, exist_ok=True); os.makedirs(sc, exist_ok=True)
    step = max(1, math.ceil(dur / 1200))                     # per-second keyframes (every Ns past 20 min)
    sh(['ffmpeg', '-v', 'error', '-i', src, '-vf', f'fps=1/{step},scale=360:-2', '-q:v', '6', f'{kf}/k%05d.jpg'], check=True)
    ks = sorted(os.listdir(kf))
    with zipfile.ZipFile(os.path.join(OUT, 'keyframes.zip'), 'w', zipfile.ZIP_STORED) as z:
        for i, n in enumerate(ks): z.write(os.path.join(kf, n), f't{i*step:05d}s.jpg')
    meta['keyframes'] = {'count': len(ks), 'every_s': step, 'file': 'keyframes.zip', 'naming': 't<second>s.jpg'}
    thr = float(OPTS.get('scene', 0.3))
    p = sh(['ffmpeg', '-v', 'info', '-i', src, '-vf', f"scale=640:-2,select='eq(n,0)+gt(scene,{thr})',showinfo", '-vsync', 'vfr', '-q:v', '3', f'{sc}/s%04d.jpg'])
    times = [float(m) for m in re.findall(r'pts_time:([\d.]+)', p.stderr)]
    files = sorted(os.listdir(sc)); picks = list(zip(times, files))[:len(files)]
    if len(picks) < 8 and dur > 4:                           # too few cuts: add evenly spaced picks
        have = {round(t) for t, _ in picks}
        for i in range(12):
            t = dur * (i + 0.5) / 12
            if round(t) in have: continue
            n = f'u{i:03d}.jpg'; sh(['ffmpeg', '-v', 'error', '-ss', f'{t:.2f}', '-i', src, '-frames:v', '1', '-vf', 'scale=640:-2', '-q:v', '3', f'{sc}/{n}'])
            if os.path.exists(f'{sc}/{n}'): picks.append((t, n))
        picks.sort()
    if len(picks) > 60: picks = [picks[round(i * (len(picks) - 1) / 59)] for i in range(60)]
    os.makedirs(os.path.join(OUT, 'scenes'), exist_ok=True); scenes = []
    for i, (t, n) in enumerate(picks):
        dst = f'scene{i+1:02d}_{t:08.2f}s.jpg'; shutil.copy(f'{sc}/{n}', os.path.join(OUT, 'scenes', dst))
        scenes.append({'n': i + 1, 't': round(t, 2), 'tc': ts(t), 'file': 'scenes/' + dst})
    for i, s in enumerate(scenes): s['end'] = scenes[i + 1]['t'] if i + 1 < len(scenes) else round(dur, 2)
    meta['scenes'] = scenes; meta['scene_threshold'] = thr
    # contact sheet
    cols = 6 if len(scenes) > 12 else 4; tw = 320
    ims = [Image.open(os.path.join(OUT, s['file'])).convert('RGB') for s in scenes]
    th = max(int(tw * im.height / im.width) for im in ims) if ims else 180
    rows = math.ceil(len(ims) / cols) or 1; head = 46
    sheet = Image.new('RGB', (cols * tw + (cols + 1) * 6, head + rows * (th + 26) + 6), (18, 18, 22)); d = ImageDraw.Draw(sheet)
    try: f1 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 15); f2 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    except Exception: f1 = f2 = ImageFont.load_default()
    pr = meta['probe']; title = ''.join(c for c in (meta.get('title') or URL) if ord(c) < 0x2000)[:90]
    d.text((8, 6), title, fill=(255, 255, 255), font=f1)
    d.text((8, 26), f"{pr['width']}x{pr['height']} @ {pr['fps_avg']} fps · {ts(pr['duration'])} · {len(scenes)} scene picks (cut threshold {thr})", fill=(170, 170, 180), font=f2)
    for i, (s, im) in enumerate(zip(scenes, ims)):
        x = 6 + (i % cols) * (tw + 6); y = head + (i // cols) * (th + 26)
        im = im.resize((tw, int(tw * im.height / im.width))); sheet.paste(im, (x, y))
        d.text((x + 2, y + im.height + 4), f"#{s['n']}  {s['tc']}", fill=(255, 210, 90), font=f2)
    sheet.save(os.path.join(OUT, 'contact_sheet.jpg'), quality=82)
    shutil.rmtree(kf, ignore_errors=True); shutil.rmtree(sc, ignore_errors=True)
def burst(src, fps):
    """every native frame (e.g. all 120 per second) inside a window: OPTS burst=START-END seconds"""
    a, b = [float(x) for x in OPTS['burst'].split('-')]; bd = os.path.join(W, 'burst'); os.makedirs(bd, exist_ok=True)
    sh(['ffmpeg', '-v', 'error', '-ss', f'{a}', '-t', f'{b-a}', '-i', src, '-vf', 'scale=480:-2', '-vsync', 'passthrough', '-frames:v', '600', '-q:v', '4', f'{bd}/f%04d.jpg'], check=True)
    fs = sorted(os.listdir(bd))
    with zipfile.ZipFile(os.path.join(OUT, 'burst.zip'), 'w', zipfile.ZIP_STORED) as z:
        for i, n in enumerate(fs): z.write(os.path.join(bd, n), f'f{i:04d}_{a + i / (fps or 30):08.3f}s.jpg')
    meta['burst'] = {'start': a, 'end': b, 'frames': len(fs), 'native_fps': fps, 'file': 'burst.zip'}; shutil.rmtree(bd, ignore_errors=True)

# ---------------- speakers ----------------
def get(url, dst):
    if not os.path.exists(dst):
        tmp = dst + '.part'; urllib.request.urlretrieve(url, tmp); os.replace(tmp, dst)
    return dst
def diarize(wav):
    gated = None
    if HF:
        try: urllib.request.urlopen(urllib.request.Request('https://huggingface.co/pyannote/speaker-diarization-3.1/resolve/main/config.yaml', headers={'Authorization': 'Bearer ' + HF}), timeout=15); gated = 'access granted'
        except Exception as e: gated = f'{type(e).__name__}: {str(e)[:120]}'
    meta['pyannote_gated_check'] = gated
    import sherpa_onnx, soundfile as sf, numpy as np
    segd = os.path.join(MODELS, 'sherpa-onnx-pyannote-segmentation-3-0')
    if not os.path.exists(os.path.join(segd, 'model.onnx')):
        tb = get('https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2', os.path.join(MODELS, 'seg.tar.bz2'))
        tarfile.open(tb).extractall(MODELS)
    emb = get('https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/wespeaker_en_voxceleb_resnet34_LM.onnx', os.path.join(MODELS, 'wespeaker_en_voxceleb_resnet34_LM.onnx'))
    n = int(OPTS.get('speakers', -1)); thr = float(OPTS.get('thr', 0.5))
    cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=os.path.join(segd, 'model.onnx')), num_threads=2),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=emb, num_threads=2),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=n, threshold=thr), min_duration_on=0.3, min_duration_off=0.5)
    if not cfg.validate(): raise RuntimeError('sherpa diarization config invalid')
    sd = sherpa_onnx.OfflineSpeakerDiarization(cfg)
    audio, sr = sf.read(wav, dtype='float32', always_2d=True); audio = audio[:, 0]
    res = sd.process(audio).sort_by_start_time()
    segs = [{'start': round(r.start, 2), 'end': round(r.end, 2), 'spk': int(r.speaker)} for r in res]
    # second pass: one voice often gets split (voice changes, noisy rooms). Merge clusters whose average voiceprints are
    # close (cosine >= merge, default 0.7; tuned on 4 clips: same speaker 0.82, different speakers 0.40).
    merge = float(OPTS.get('merge', 0.7)); merged = []
    if n <= 0 and len({s['spk'] for s in segs}) > 1 and merge < 1:
        ext = sherpa_onnx.SpeakerEmbeddingExtractor(sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=emb, num_threads=2))
        def vec(a):
            st = ext.create_stream(); st.accept_waveform(16000, a); st.input_finished(); v = np.array(ext.compute(st)); return v / (np.linalg.norm(v) + 1e-9)
        vs = {}
        for s in segs:
            a, b = s['start'], s['end']
            if b - a < 0.5: continue
            t = a
            while True:
                e = min(b, t + 1.5); vs.setdefault(s['spk'], []).append(vec(audio[int(t * 16000):int(e * 16000)]))
                t += 0.75
                if t + 0.5 > b or e >= b: break
        cen = {k: np.mean(v, axis=0) for k, v in vs.items()}
        cen = {k: v / np.linalg.norm(v) for k, v in cen.items()}
        meta['speaker_similarity_before_merge'] = {f'{a}-{b}': round(float(cen[a] @ cen[b]), 3) for a in cen for b in cen if a < b}
        while len(cen) > 1:
            ks = sorted(cen); best = max(((float(cen[a] @ cen[b]), a, b) for i, a in enumerate(ks) for b in ks[i + 1:]))
            if best[0] < merge: break
            _, a, b = best; merged.append([a, b, round(best[0], 3)])
            for s in segs:
                if s['spk'] == b: s['spk'] = a
            cen[a] = (cen[a] * len(vs[a]) + cen[b] * len(vs[b])); cen[a] /= np.linalg.norm(cen[a]); vs[a] += vs.pop(b); del cen[b]
    order = {}                                               # renumber speakers by first appearance: SPEAKER 1, 2, ...
    for s in segs: order.setdefault(s['spk'], len(order) + 1)
    for s in segs: s['speaker'] = f"SPEAKER {order[s['spk']]}"; del s['spk']
    meta['diarizer'] = {'engine': 'sherpa-onnx (pyannote segmentation-3.0 ONNX + WeSpeaker ResNet34 embeddings, not gated)', 'cluster_threshold': thr, 'num_speakers_forced': n if n > 0 else None, 'speakers_found': len(order), 'segments': len(segs), 'voiceprint_merge': merge, 'merged_pairs': merged}
    return segs
def who(a, b, segs):
    best, bo = None, 0.0
    for s in segs:
        o = min(b, s['end']) - max(a, s['start'])
        if o > bo: best, bo = s['speaker'], o
    if best: return best
    mid = (a + b) / 2; near = min(segs, key=lambda s: min(abs(mid - s['start']), abs(mid - s['end'])), default=None)
    return near['speaker'] if near and min(abs(mid - near['start']), abs(mid - near['end'])) < 1.5 else 'SPEAKER ?'
def utterances(words):
    utts = []
    for w in words:
        u = utts[-1] if utts else None
        long_ = u and (u['end'] - u['start'] > 25 or (u['text'].endswith(('.', '?', '!', ',')) and u['end'] - u['start'] > 12))
        if u and u['speaker'] == w['speaker'] and w['start'] - u['end'] < 1.5 and not long_:
            u['text'] += w['word']; u['end'] = w['end']; u['words'] += 1
        else: utts.append({'speaker': w['speaker'], 'start': w['start'], 'end': w['end'], 'text': w['word'].strip(), 'words': 1})
    for u in utts: u['text'] = u['text'].strip(); u['tc'] = ts(u['start'])
    return utts
def write_md(utts, path, title, partial=False):
    with open(path, 'w') as f:
        f.write(f"# Transcript{' (partial, still running)' if partial else ''}: {title}\n\n")
        if not utts and not partial:
            w = meta.get('whisper', {}); f.write(f"(no speech detected: the voice detector kept {w.get('speech_s_after_vad')} s of {meta['probe']['duration']:.1f} s; likely music or no talking)\n")
        for u in utts: f.write(f"[{u['tc']}] **{u['speaker']}:** {u['text']}\n\n")
def write_srt(utts, path):
    n = 0
    with open(path, 'w') as f:
        for u in utts:
            ws = u['text'].split(); k = max(1, math.ceil(max(len(u['text']) / 84, (u['end'] - u['start']) / 7)))
            per = math.ceil(len(ws) / k); dt = (u['end'] - u['start']) / k
            for i in range(k):
                part = ' '.join(ws[i * per:(i + 1) * per])
                if not part: continue
                n += 1; a = u['start'] + i * dt
                f.write(f"{n}\n{ts(a, True)} --> {ts(a + dt, True)}\n{u['speaker']}: {part}\n\n")

# ---------------- main ----------------
def main():
    src = fetch()
    if not src:
        meta['errors'].append('fetch failed on every route'); finish(False); return
    info = {}
    try: info = json.load(open(os.path.join(W, 'src.info.json')))
    except Exception: pass
    meta.update({'title': info.get('title'), 'uploader': info.get('uploader') or info.get('channel'), 'webpage_url': info.get('webpage_url') or URL,
                 'source_format': {k: info.get(k) for k in ('format', 'format_id', 'fps', 'width', 'height', 'vcodec', 'acodec', 'ext')}, 'description': (info.get('description') or '')[:1500]})
    meta['probe'] = pr = probe(src); log('probe', pr)
    meta['native_fps'] = pr['fps_avg']
    json.dump(meta, open(os.path.join(OUT, 'meta.json'), 'w'), indent=1)
    live(stage='frames', title=meta['title'], duration=pr['duration'], fps=pr['fps_avg'], files=[os.path.join(OUT, 'meta.json')])
    try:
        frames(src, pr['duration'])
        if OPTS.get('burst'): burst(src, pr['fps_avg'])
    except Exception as e: meta['errors'].append(f'frames: {type(e).__name__}: {str(e)[:500]}'); traceback.print_exc()
    json.dump(meta, open(os.path.join(OUT, 'meta.json'), 'w'), indent=1)
    live(stage='audio', scenes=len(meta.get('scenes', [])), files=[os.path.join(OUT, 'contact_sheet.jpg'), os.path.join(OUT, 'meta.json')])
    if not pr['has_audio']:
        meta['errors'].append('no audio stream in the source'); finish(True); return
    wav = os.path.join(W, 'a16.wav'); sh(['ffmpeg', '-v', 'error', '-y', '-i', src, '-ac', '1', '-ar', '16000', wav], check=True)
    segs = []
    try:
        live(stage='speakers'); segs = diarize(wav); log('diarized', meta['diarizer'])
    except Exception as e: meta['errors'].append(f'diarization: {type(e).__name__}: {str(e)[:500]}'); traceback.print_exc()
    json.dump({'segments': segs}, open(os.path.join(OUT, 'speakers.json'), 'w'), indent=1)
    from faster_whisper import WhisperModel
    model = OPTS.get('model', 'small'); live(stage='transcribing', model=model)
    wm = WhisperModel(model, device='cpu', compute_type='int8', cpu_threads=os.cpu_count() or 2, download_root=os.path.join(MODELS, 'whisper'))
    it, tinfo = wm.transcribe(wav, language=OPTS.get('lang'), language_detection_segments=4, word_timestamps=True, vad_filter=True, beam_size=int(OPTS.get('beam', 5)),
                              condition_on_previous_text=False, vad_parameters={'min_silence_duration_ms': 500})
    meta['whisper'] = {'model': model, 'language': tinfo.language, 'language_prob': round(tinfo.language_probability, 3), 'speech_s_after_vad': round(getattr(tinfo, 'duration_after_vad', 0) or 0, 1)}
    words, segs_out, last_push = [], [], time.time(); title = meta.get('title') or URL
    pmd, pjs = os.path.join(W, 'partial.md'), os.path.join(W, 'partial.json')
    for s in it:
        segs_out.append({'start': round(s.start, 2), 'end': round(s.end, 2), 'text': s.text.strip(), 'no_speech_prob': round(s.no_speech_prob, 3), 'avg_logprob': round(s.avg_logprob, 3)})
        for w in (s.words or []):
            words.append({'start': round(w.start, 2), 'end': round(w.end, 2), 'word': w.word, 'p': round(w.probability, 3),
                          'speaker': who(w.start, w.end, segs) if segs else 'SPEAKER 1'})
        if time.time() - last_push > float(OPTS.get('chunk', 30)):
            utts = utterances(words); write_md(utts, pmd, title, partial=True)
            json.dump({'audio_done_s': round(s.end, 2), 'duration': pr['duration'], 'utterances': utts}, open(pjs, 'w'), indent=1)
            live(stage='transcribing', audio_done_s=round(s.end, 1), pct=round(100 * s.end / max(pr['duration'], 1)), utterances=len(utts),
                 partial_tail=[f"[{u['tc']}] {u['speaker']}: {u['text']}" for u in utts[-3:]], files=[pmd, pjs]); last_push = time.time()
    utts = utterances(words); meta['speakers_in_transcript'] = sorted({u['speaker'] for u in utts})
    write_md(utts, os.path.join(OUT, 'transcript.md'), title); write_srt(utts, os.path.join(OUT, 'transcript.srt'))
    json.dump({'title': title, 'url': URL, 'language': tinfo.language, 'model': model, 'utterances': utts, 'segments': segs_out, 'words': words, 'diarization': segs},
              open(os.path.join(OUT, 'transcript.json'), 'w'), indent=1)
    # scenes x transcript: what was said during each scene pick
    for sc in meta.get('scenes', []):
        sc['said'] = ' '.join(f"{u['speaker']}: {u['text']}" for u in utts if u['start'] < sc['end'] and u['end'] > sc['t'])[:600]
    finish(True)
def finish(ok):
    meta['ok'] = ok; meta['total_s'] = round(time.time() - T0, 1)
    json.dump(meta, open(os.path.join(OUT, 'meta.json'), 'w'), indent=1)
    if api:
        try:
            api.upload_folder(folder_path=OUT, path_in_repo=f'runs/{RUN_ID}', repo_id=DS, repo_type='dataset', commit_message=f'video-watch {REQ} run {RUN_ID}')
        except Exception as e: meta['errors'].append(f'final upload: {e}'); log('final upload failed', e)
    live(stage='done' if ok else 'failed', ok=ok, errors=meta['errors'], fetch_attempts=meta['fetch_attempts'], files=[os.path.join(OUT, 'meta.json')])
    log('DONE ok=%s' % ok, json.dumps(meta['errors'])[:800])
if __name__ == '__main__':
    try: main()
    except Exception as e:
        traceback.print_exc(); meta['errors'].append(f'crash: {type(e).__name__}: {str(e)[:600]}'); finish(False); sys.exit(1)
