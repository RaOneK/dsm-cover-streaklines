#!/usr/bin/env python3
"""Local copy 04.11.2026 of the parts of code/postprocessing/cover_streaklines_20261103/render_cover_seq.py that
render_cover_seq_refine.py imports (sources, field, time-continuous Seq, RK4). The iCloud copy was evicted from the Mac
(disk 99 % full) and could not be downloaded; content as of the COVER_NTOP / COVER_TOPMAX edit of 04.11.2026."""
import os, sys
from pathlib import Path
import numpy as np

RUNNER = Path.home()/'Documents/DSM_Fortran/dsm_local_runner/runner/cluster_original'
SEAGATE = Path('/Volumes/Seagate/BL separation/DSM_storage_20260907')
CASE = os.environ.get('COVER_CASE', 'cover_long_20261103_Re5000_k2pi_A0p95')
PERIOD = Path(os.environ.get('COVER_PERIOD', '/nonexistent'))   # native_phase folder; main sets it from argv
START_PERIOD = 2                # dye release starts at the first frame of this period (after the forcing ramp)
N_ROOF, ROOF_X0, ROOF_X1, ROOF_DY = int(os.environ.get('COVER_NROOF', 120)), 0.06, 4.94, 0.002
FRAME_GAP = 16                  # phase intervals (1/8 period) between the frames of the cover
SUBRK = 4                       # RK4 substeps per phase interval, as painted_depth
OUT = SEAGATE/'postprocessing/cover_streaklines_20261103'/os.environ.get('COVER_OUT', 'may_like_Re5000')

X_SRC = 0.041
N_LOW, Y_LOW0, Y_LOW1 = 6, 0.004, 0.03
N_MID, Y_MID1 = 10, 0.20
N_UP, Y_UP1 = 24, 0.49
N_TOP, Y_TOP0 = 24, 0.35
NSUB = 16
NFRAMES = int(os.environ.get('COVER_NFRAMES', 12))
W_OUT, H_OUT, GUTTER = 5100, 6600, 30
SS, LINE_SS, JOIN_MAX = 3, 9, 0.08
SMOOTH = NSUB + 1
X_LO, X_HI = 0.04, 5.0
Y_TOP = float(os.environ.get('COVER_H', 0.5))
WORKERS = 6
Y_CROP = 1.0
F17 = '%.17g'
MAY_ROWS = os.environ.get('COVER_MAYROWS', '0') == '1'
PROG = None


def rows(scale=1):
    if MAY_ROWS:
        lo = np.linspace(Y_LOW0, Y_LOW1, max(2, N_LOW//scale))
        dense = os.environ.get('COVER_TOPDENSE', '1') == '1'
        ntop, tmax = int(os.environ.get('COVER_NTOP', 30)), float(os.environ.get('COVER_TOPMAX', 0.995))
        base = np.linspace(0.02*Y_TOP, (min(0.98, tmax) if dense else 0.85)*Y_TOP, max(2, 34//scale))
        top = np.linspace(0.70*Y_TOP, tmax*Y_TOP, max(2, ntop//scale)) if dense and ntop > 0 else np.empty(0)
        hs = np.concatenate((lo, base, top)); band = np.array(['wall']*len(lo) + ['base']*len(base) + ['top']*len(top))
        o = np.argsort(hs)
        return hs[o], band[o]
    lo = np.linspace(Y_LOW0, Y_LOW1, max(2, N_LOW//scale))
    mid = np.linspace(Y_LOW1, Y_MID1, max(2, N_MID//scale) + 1)[1:]
    up = np.linspace(Y_MID1, Y_UP1, max(2, N_UP//scale) + 1)[1:]
    top = np.linspace(Y_TOP0, Y_UP1, max(2, N_TOP//scale) + 2)[1:-1]
    top = top[np.min(np.abs(top[:, None] - up[None, :]), axis=1) > 1e-4]
    hs = np.concatenate((lo, mid, up, top)); band = np.array(['wall']*len(lo) + ['middle']*len(mid) + ['upper']*len(up) + ['top']*len(top))
    o = np.argsort(hs)
    return hs[o], band[o]


def periods():
    return sorted(PERIOD.glob('period_*.bin'))


def field(path=None):
    sys.path.insert(0, str(RUNNER))
    import painted_depth as pdp
    d = pdp.read_native(str(path or periods()[0])); n = int(np.searchsorted(d['y'], Y_CROP)) + 2
    d['y'] = d['y'][:n]; d['psi'] = d['psi'][:, :n, :]
    return pdp.Field(d)


class Seq:
    """Saved periods in order; interval n runs from frame n to frame n+1 of the whole sequence."""
    def __init__(self, first):
        self.files = periods()[first - 1:]; self.p = -1; self.cur = self.nxt = None
        self.F0 = field(self.files[0]); self.nph = self.F0.nph; self.dt_phase = self.F0.dt_phase

    def frames(self, n):
        p, k = divmod(n, self.nph)
        if p != self.p:
            self.cur = self.nxt if (self.nxt is not None and p == self.p + 1) else field(self.files[p])
            self.nxt = None; self.p = p
        if k < self.nph - 1:
            return self.cur, k, self.cur, k + 1
        if self.nxt is None: self.nxt = field(self.files[p + 1])
        return self.cur, k, self.nxt, 0

    def uv(self, n, xp, yp, frac):
        A, ka, B, kb = self.frames(n); bl = A._bilin
        return (bl(A.u[ka], B.u[kb], frac, A.xu, A.yu, xp, yp), bl(A.v[ka], B.v[kb], frac, A.xv, A.yv, xp, yp))

    def step(self, xp, yp, n):
        h = self.dt_phase/SUBRK
        for s in range(SUBRK):
            f0 = s/SUBRK; fm = (s + .5)/SUBRK; f1 = (s + 1)/SUBRK
            u1, v1 = self.uv(n, xp, yp, f0)
            u2, v2 = self.uv(n, xp + .5*h*u1, yp + .5*h*v1, fm)
            u3, v3 = self.uv(n, xp + .5*h*u2, yp + .5*h*v2, fm)
            u4, v4 = self.uv(n, xp + h*u3, yp + h*v3, f1)
            xp = xp + h*(u1 + 2*u2 + 2*u3 + u4)/6; yp = np.maximum(yp + h*(v1 + 2*v2 + 2*v3 + v4)/6, 0.)
        return xp, yp
