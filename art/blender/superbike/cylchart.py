"""Cylinder chart round a fore-aft axis, for bodywork fitted to the reference scan (tank, tail).

A chart point (u, v): v = y (bike fore-aft), u = Rc * theta, theta measured from straight up round the
axis (x = 0, z = zc + slope * (v - v0)), +u toward the bike's left (+X). The skin point is at distance h(u, v)
inward from the cylinder of radius Rc: P = axis(v) + (Rc - h) * (sin theta, 0, cos theta). Sections are the
planes y = v (a sloped axis just shears the cylinder, e.g. to follow a rising tail).
Same interface as fairings.Surface (point / normal / derivs / to_flat / from_flat), so fairings.panel()
builds panels on it: outlines are drawn in (u, v), triangulated in a flattened copy (s = 3D arc length
round the section from the top centre line).
"""
import math

import numpy as np
from scipy.interpolate import RectBivariateSpline


class CylSurface:
    def __init__(self, H, us, vs, zc, Rc, slope=0.0, v0=0.0):
        self.H, self.us, self.vs, self.zc, self.Rc = H, us, vs, zc, Rc
        self.slope, self.v0 = slope, v0
        self.spl = RectBivariateSpline(vs, us, H, kx=3, ky=3)
        uf = np.linspace(us[0], us[-1], 801)
        self.vf = np.linspace(vs[0], vs[-1], 151)
        Uf, Vf = np.meshgrid(uf, self.vf)
        Su, _ = self.derivs(Uf, Vf)
        sp = np.linalg.norm(Su, axis=-1)
        S = np.concatenate([np.zeros((len(self.vf), 1)), np.cumsum((sp[:, 1:] + sp[:, :-1]) / 2 * np.diff(uf), axis=1)], 1)
        mid = np.argmin(np.abs(uf))
        S -= S[:, [mid]]
        self.s_spl = RectBivariateSpline(self.vf, uf, S, kx=3, ky=3)
        # inverse s -> u per row over the widest s of any row; rows that end sooner carry on along their end slope
        self.sf = np.linspace(S[:, 0].min(), S[:, -1].max(), 801)
        rows = []
        for row in S:
            ui = np.interp(self.sf, row, uf)
            lo, hi = self.sf < row[0], self.sf > row[-1]
            ui[lo] = uf[0] + (self.sf[lo] - row[0]) * (uf[1] - uf[0]) / (row[1] - row[0])
            ui[hi] = uf[-1] + (self.sf[hi] - row[-1]) * (uf[-1] - uf[-2]) / (row[-1] - row[-2])
            rows.append(ui)
        Ui = np.stack(rows)
        self.u_spl = RectBivariateSpline(self.vf, self.sf, Ui, kx=3, ky=3)

    def h(self, u, v, du=0, dv=0):
        return self.spl(v, u, dx=dv, dy=du, grid=False)

    def point(self, u, v):
        u, v = np.broadcast_arrays(np.asarray(u, float), np.asarray(v, float))
        th = u / self.Rc
        r = self.Rc - self.h(u, v)
        return np.stack([r * np.sin(th), v, self.zc + self.slope * (v - self.v0) + r * np.cos(th)], -1)

    def derivs(self, u, v):
        u, v = np.broadcast_arrays(np.asarray(u, float), np.asarray(v, float))
        th = u / self.Rc
        h, hu, hv = self.h(u, v), self.h(u, v, du=1), self.h(u, v, dv=1)
        r = self.Rc - h
        s, c = np.sin(th), np.cos(th)
        Su = np.stack([-hu * s + r * c / self.Rc, np.zeros_like(u), -hu * c - r * s / self.Rc], -1)
        Sv = np.stack([-hv * s, np.ones_like(u), self.slope - hv * c], -1)
        return Su, Sv

    def normal(self, u, v):
        Su, Sv = self.derivs(u, v)
        n = np.cross(Su, Sv)
        return n / np.linalg.norm(n, axis=-1, keepdims=True)

    def to_flat(self, u, v):
        return self.s_spl(v, u, grid=False)

    def from_flat(self, s, v):
        return self.u_spl(v, s, grid=False)


def sample(bvh, zc, Rc, urange, vrange, step=0.004, outward=False, slope=0.0, v0=0.0):
    """Depth grid H[v, u]. outward=True casts from the axis out (first hit = skin seen from inside,
    so parts below - like the rear tyre under the tail - can't block it)."""
    from mathutils import Vector
    us = np.arange(urange[0], urange[1] + 1e-9, step)
    vs = np.arange(vrange[0], vrange[1] + 1e-9, step)
    H = np.full((len(vs), len(us)), np.nan)
    for j, u in enumerate(us):
        th = u / Rc
        d = Vector((math.sin(th), 0.0, math.cos(th)))
        for i, v in enumerate(vs):
            a = Vector((0.0, v, zc + slope * (v - v0)))
            if outward:
                hit = bvh.ray_cast(a, d, Rc)
                if hit[0] is not None:
                    H[i, j] = Rc - hit[3]
            else:
                hit = bvh.ray_cast(a + d * Rc, -d, Rc)
                if hit[0] is not None:
                    H[i, j] = hit[3]
    return H, us, vs


def pfit(H, us, vs, mask, ku=0.04, kv=0.04, lam=1.0, iters=4, sub=2, out_step=0.01, symmetric=True):
    """Penalised tensor B-spline fit inside mask (robust, outliers dropped); returns a smooth grid."""
    from scipy.interpolate import BSpline
    import scipy.sparse as sps
    import scipy.sparse.linalg as spl

    def basis(x, lo, hi, step):
        n_in = int(np.ceil((hi - lo) / step))
        t = lo + np.arange(-3, n_in + 4) * (hi - lo) / n_in
        return BSpline.design_matrix(np.clip(x, lo, hi - 1e-9), t, 3)

    if symmetric:
        Hm = H[:, ::-1]
        both = np.isfinite(H) & np.isfinite(Hm)
        H = np.where(both, np.where(np.abs(H - Hm) < 0.015, (H + Hm) / 2, np.maximum(H, Hm)), np.where(np.isfinite(H), H, Hm))
        mask = mask & mask[:, ::-1]
    m = mask & np.isfinite(H)
    U, V = np.meshgrid(us, vs)
    sel = (slice(None, None, sub), slice(None, None, sub))
    Us, Vs, Hs, Ms = U[sel].ravel(), V[sel].ravel(), H[sel].ravel(), m[sel].ravel()
    idx = np.where(Ms)[0]
    u0, u1, v0, v1 = us[0], us[-1], vs[0], vs[-1]
    Bu = basis(Us[idx], u0, u1, ku).toarray()
    Bv = basis(Vs[idx], v0, v1, kv).toarray()
    nu, nv = Bu.shape[1], Bv.shape[1]
    B = sps.csr_matrix(np.einsum('ij,ik->ijk', Bv, Bu).reshape(len(idx), -1))

    def D2(n):
        return sps.diags([1, -2, 1], [0, 1, 2], shape=(n - 2, n))
    Pen = lam * (sps.kron(sps.eye(nv), D2(nu)).T @ sps.kron(sps.eye(nv), D2(nu)) + sps.kron(D2(nv), sps.eye(nu)).T @ sps.kron(D2(nv), sps.eye(nu)))
    Pen = Pen + 1e-6 * sps.eye(nu * nv)
    y = Hs[idx]
    wk = np.ones(len(idx))
    for it in range(iters):
        c = spl.spsolve((B.T @ sps.diags(wk) @ B + Pen).tocsc(), B.T @ (wk * y))
        r = y - B @ c
        sd = np.sqrt(np.average(r ** 2, weights=wk))
        wk = np.where(np.abs(r) > max(2.5 * sd, 0.003), 0.0, 1.0)
        print(f"fit pass {it}: rms {sd * 1000:.2f} mm, {np.sum(wk == 0)} of {len(wk)} dropped")
    uo = np.linspace(u0, u1, int(round((u1 - u0) / out_step)) + 1)
    vo = np.linspace(v0, v1, int(round((v1 - v0) / out_step)) + 1)
    F = basis(vo, v0, v1, kv).toarray() @ c.reshape(nv, nu) @ basis(uo, u0, u1, ku).toarray().T
    return F, uo, vo
