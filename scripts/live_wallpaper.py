#!/usr/bin/env python3
"""Phone Live Photo of the cover streaklines (04.11.2026, author): the phone wallpaper of
wallpaper_piv_lid_H1_mayband_mid_top_refined animated over one forcing period.
Stage 1 (advect): the dye of render_cover_seq_refine.py (same sources, RK4, point insertion D_INS=0.006, GAP 1/256),
  particles saved at every phase step of the last 128+80 steps (each of the six strips runs one period).
Stage 2 (frames): 128 frames; in frame k strip i shows step f_i - 127 + k, f_i the step of strip i of the still
  wallpaper (so the last frame is the still). Drawn directly at the phone size 1290x2796 (central part of the plate as
  the still wallpaper), 3x raster, line width scaled from the cover, laser-green colouring of wallpaper_piv.py.
Stage 3: ffmpeg H.264 MOV at FPS, still JPEG = last frame, makelive (github.com/RhetTbull/makelive) -> .pvt package.
Usage: live_wallpaper.py <native_phase folder> <output folder>"""
import multiprocessing as mp, os, subprocess, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import render_cover_seq as rc

D_INS, GAP_MIN, JOIN_MAX, NSUB = 0.006, 1/256, 0.08, rc.NSUB
NPER_FR, NSTRIP, FPS = 128, 6, 40
PW, PH = 1290, 2796
SRC_W, SRC_H, PANEL_H, GUT = 5100, 6600, 1028, 86        # geometry of the white cover the still wallpaper was cut from
CW = round(SRC_H*PW/PH); CX0 = (SRC_W - CW)//2; SC = PW/CW
SS = 3; LW = max(1, round(rc.LINE_SS*SC))                 # 9 raster px at 5100 -> the same stroke at the phone size
LASER = np.array([40, 255, 50], float)/255


def order_of(S, A):
    return np.lexsort((-A, S))


def refine(X, Y, S, A):
    o = order_of(S, A); X, Y, S, A = X[o], Y[o], S[o], A[o]
    if len(X) < 2:
        return X, Y, S, A
    dA = A[:-1] - A[1:]
    link = (S[:-1] == S[1:]) & (dA <= 1 + 1e-9)
    i = np.flatnonzero(link & (dA > GAP_MIN*(1 + 1e-9)) & (np.hypot(np.diff(X), np.diff(Y)) > D_INS))
    if not len(i):
        return X, Y, S, A
    n = len(X)
    has0 = np.zeros(len(i), bool); has3 = np.zeros(len(i), bool)
    has0[i > 0] = link[i[i > 0] - 1]; has3[i + 2 < n] = link[i[i + 2 < n] + 1]
    i0 = np.where(has0, i - 1, i); i3 = np.where(has3, i + 2, i + 1); cr = has0 & has3
    mx = np.where(cr, (-X[i0] + 9*X[i] + 9*X[i + 1] - X[i3])/16, .5*(X[i] + X[i + 1]))
    my = np.maximum(np.where(cr, (-Y[i0] + 9*Y[i] + 9*Y[i + 1] - Y[i3])/16, .5*(Y[i] + Y[i + 1])), 0.)
    return (np.concatenate((X, mx)), np.concatenate((Y, my)), np.concatenate((S, S[i])), np.concatenate((A, .5*(A[i] + A[i + 1]))))


def advect(args):
    ids, sx_all, sy_all, last, first_dump, ymem, dump = args
    F = rc.Seq(rc.START_PERIOD); sx = np.asarray(sx_all)[ids]; h = np.asarray(sy_all)[ids]
    X = np.empty(0); Y = np.empty(0); S = np.empty(0, int); A = np.empty(0); jj = np.arange(NSUB)
    for n in range(last):
        u0, v0 = F.uv(n, sx, h, 0.0)
        tau = jj*F.dt_phase/NSUB
        X = np.concatenate((X, (sx[:, None] + np.outer(u0, tau)).ravel())); Y = np.concatenate((Y, np.repeat(h, NSUB)))
        S = np.concatenate((S, np.repeat(ids, NSUB))); A = np.concatenate((A, np.tile(n*NSUB - jj, len(ids)).astype(float)))
        X, Y = F.step(X, Y, n)
        k = (X < rc.X_HI) & (Y < ymem); X, Y, S, A = X[k], Y[k], S[k], A[k]
        X, Y, S, A = refine(X, Y, S, A)
        if n + 1 >= first_dump:
            np.savez(Path(dump)/('w%03d_n%06d.npz' % (ids[0], n + 1)), X=X.astype(np.float32), Y=Y.astype(np.float32),
                     S=S.astype(np.int32), A=A.astype(np.float32))
        with rc.PROG.get_lock(): rc.PROG.value += 1
    return True


def init(p):
    rc.PROG = p


def load(dump, m):
    d = [np.load(f) for f in sorted(Path(dump).glob('w*_n%06d.npz' % m))]
    X, Y, S, A = (np.concatenate([q[c] for q in d]).astype(float) if c in 'XYA' else np.concatenate([q[c] for q in d]) for c in 'XYSA')
    o = order_of(S, A)
    return X[o], Y[o], S[o], A[o]


def colour(g):
    a = np.asarray(g, float)/255
    glow = np.asarray(g.filter(ImageFilter.GaussianBlur(radius=max(2, g.size[0]//600))), float)/255
    core = np.clip(a, 0, 1)[..., None]*(0.75*LASER + 0.25)
    halo = np.clip(1.3*glow, 0, 1)[..., None]*LASER*0.55
    return Image.fromarray((np.clip(core + halo, 0, 1)*255).astype(np.uint8))


def frame(args):
    k, steps, dump, outdir, ymax = args
    W, H = PW*SS, PH*SS; img = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(img)
    for i, m in enumerate(steps):
        X, Y, S, A = load(dump, m)
        gx = (X - rc.X_LO)/(rc.X_HI - rc.X_LO)*(SRC_W - 1)                       # cover pixels
        gy = i*(PANEL_H + GUT) + (1 - Y/ymax)*(PANEL_H - 1)
        px = (gx - CX0)*SC*SS; py = gy*SC*SS
        brk = np.ones(len(S), bool)
        brk[1:] = (S[1:] != S[:-1]) | (A[:-1] - A[1:] > 1 + 1e-9) | (np.hypot(np.diff(X), np.diff(Y)) > JOIN_MAX)
        starts = np.flatnonzero(brk); ends = np.append(starts[1:], len(S))
        sm = rc.SMOOTH; kk = np.ones(sm)/sm; hw = sm//2
        for a, b in zip(starts, ends):
            if b - a > sm:
                px[a + hw:b - hw] = np.convolve(px[a:b], kk, 'valid'); py[a + hw:b - hw] = np.convolve(py[a:b], kk, 'valid')
        vis = (px > -50) & (px < W + 50)
        for a, b in zip(starts, ends):
            if b - a >= 2 and vis[a:b].any():
                dr.line(list(zip(px[a:b].tolist(), py[a:b].tolist())), fill=255, width=LW, joint='curve')
    g = img.resize((PW, PH), Image.Resampling.LANCZOS)
    colour(g).save(Path(outdir)/('f%04d.png' % k))
    return k


def main():
    per, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    rc.PERIOD = per; os.environ['COVER_PERIOD'] = str(per)
    dump = out/'particles_dump'; frames_dir = out/'frames'
    dump.mkdir(parents=True, exist_ok=True); frames_dir.mkdir(parents=True, exist_ok=True)
    F = rc.field(); last = (len(rc.periods()) - rc.START_PERIOD + 1)*F.nph - 1
    fst = [last - (NSTRIP - 1 - i)*rc.FRAME_GAP for i in range(NSTRIP)]
    first_dump = fst[0] - (NPER_FR - 1)
    hs, band = rc.rows(1); sx = np.full(len(hs), rc.X_SRC); ymax = rc.Y_TOP*(1 - 1e-9)
    t0 = time.time()
    if '--frames-only' not in sys.argv:
        chunks = [np.arange(len(hs))[w::rc.WORKERS] for w in range(rc.WORKERS)]
        prog = mp.Value('l', 0); total = last*len(chunks)
        print('live wallpaper: %d rows, %d intervals, dump from step %d, output %s' % (len(hs), last, first_dump, out), flush=True)
        with mp.Pool(len(chunks), initializer=init, initargs=(prog,)) as pool:
            res = pool.map_async(advect, [(c, sx, hs, last, first_dump, ymax, str(dump)) for c in chunks])
            while not res.ready():
                res.wait(5); d = prog.value; el = time.time() - t0
                eta = el*(total - d)/d if d else float('nan')
                print('\r\033[2K[1/3] advect %5.1f%%  elapsed %dm%02ds  ETA %s' % (100*d/total, el//60, el % 60,
                      '--' if not np.isfinite(eta) else '%dm%02ds' % (eta//60, eta % 60)), end='', flush=True)
            res.get()
        print('\nadvection done in %.1f min' % ((time.time() - t0)/60), flush=True)
    t1 = time.time(); jobs = [(k, [f - (NPER_FR - 1) + k for f in fst], str(dump), str(frames_dir), ymax) for k in range(NPER_FR)]
    with mp.Pool(rc.WORKERS) as pool:
        for j, _ in enumerate(pool.imap_unordered(frame, jobs)):
            el = time.time() - t1
            print('\r\033[2K[2/3] frames %d/%d %3.0f%%  ETA %ds' % (j + 1, NPER_FR, 100*(j + 1)/NPER_FR, el/(j + 1)*(NPER_FR - j - 1)), end='', flush=True)
    print(flush=True)
    mov = out/'COVER_LIVE.mov'; jpg = out/'COVER_LIVE.jpg'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(frames_dir/'f%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '14', '-preset', 'slow', '-movflags', '+faststart', str(mov)], check=True)
    Image.open(frames_dir/('f%04d.png' % (NPER_FR - 1))).convert('RGB').save(jpg, quality=95)
    mp4 = out/'COVER_LIVE_preview.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(mov), '-c', 'copy', str(mp4)], check=True)
    mk = Path.home()/'Documents/DSM_Fortran/cover_livephoto/venv/bin/makelive'
    subprocess.run([str(mk), '--pvt', '--manual', str(jpg), str(mov)], check=True)
    print('[3/3] LIVE_DONE %s (%.1f min)' % (out, (time.time() - t0)/60), flush=True)


if __name__ == '__main__':
    main()
