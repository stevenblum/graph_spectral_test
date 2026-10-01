"""Graph-learning solvers for Lesson 4 (`04_learning_temperature_graphs.ipynb`).

Every learner returns a **weight vector** `w` on the upper triangle of an N x N
adjacency matrix.  Parameterising by `w >= 0` rather than by L directly makes
Laplacian validity *structural*:

    W = offdiag(w),  L = diag(W 1) - W   ==>   L = L^T,  L 1 = 0,  L_ij <= 0 (i != j)

so no learned matrix ever has to be "repaired" after the fact.  This also
conditions the convex programs far better than constraining a symmetric matrix
variable; see `notes` in the notebook.

Conventions
-----------
Y : (N, T) real, stations in rows, days in columns, already centred.
All learners are deterministic given their arguments and any `seed`.
"""

from __future__ import annotations

import time
import numpy as np
import scipy.sparse as sp

__all__ = [
    "EdgeIndex", "L_from_w", "w_from_L", "rescale_trace", "n_components",
    "gaussian_weights", "knn_sparsify", "correlation_weights",
    "kalofolias", "gl_sigrep", "fgl_3sr", "igl_3sr", "esa_gl",
]


# --------------------------------------------------------------------------
# edge bookkeeping
# --------------------------------------------------------------------------
class EdgeIndex:
    """Upper-triangle edge indexing and the degree operator for a fixed N."""

    def __init__(self, N: int):
        self.N = N
        self.iu = np.triu_indices(N, 1)
        self.m = len(self.iu[0])
        rows = np.concatenate([self.iu[0], self.iu[1]])
        cols = np.concatenate([np.arange(self.m), np.arange(self.m)])
        # deg = Sdeg @ w
        self.Sdeg = sp.csr_matrix((np.ones(2 * self.m), (rows, cols)),
                                  shape=(N, self.m))
        self._rows, self._cols = rows, cols

    def W(self, w):
        W = np.zeros((self.N, self.N))
        W[self.iu] = w
        return W + W.T

    def L(self, w):
        W = self.W(w)
        return np.diag(W.sum(1)) - W

    def vec(self, W):
        return np.asarray(W)[self.iu]

    def pair_distance(self, M):
        """d_e = M_ii + M_jj - 2 M_ij for each edge e=(i,j)."""
        d = np.diag(M)
        return d[self.iu[0]] + d[self.iu[1]] - 2.0 * M[self.iu]

    def neighbour_map(self, V):
        """List of sparse G_c with (W(w) V)[:, c] = G_c @ w."""
        out = []
        for c in range(V.shape[1]):
            v = V[:, c]
            data = np.concatenate([v[self.iu[1]], v[self.iu[0]]])
            out.append(sp.csr_matrix((data, (self._rows, self._cols)),
                                     shape=(self.N, self.m)))
        return out


def L_from_w(w, N):
    return EdgeIndex(N).L(np.asarray(w))


def w_from_L(L):
    N = L.shape[0]
    return np.maximum(-np.asarray(L)[np.triu_indices(N, 1)], 0.0)


def rescale_trace(w, N, target=None):
    """Scale weights so that tr(L) = target (default N). tr(L) = 2 * sum(w)."""
    target = N if target is None else target
    s = 2.0 * np.sum(w)
    return w * (target / s) if s > 0 else w


def n_components(L, tol=1e-8):
    ev = np.linalg.eigvalsh((L + L.T) / 2.0)
    return int(np.sum(ev < tol))


# --------------------------------------------------------------------------
# A / B : kernel constructions (no optimisation)
# --------------------------------------------------------------------------
def gaussian_weights(D2, sigma2):
    """w_ij = exp(-D2_ij / sigma2) on the upper triangle. D2 is squared distance."""
    return np.exp(-D2 / sigma2)


def knn_sparsify(w, ei: EdgeIndex, k: int):
    """Keep an edge if either endpoint ranks it among its k heaviest (symmetric OR)."""
    W = ei.W(w)
    np.fill_diagonal(W, -np.inf)
    keep = np.zeros_like(W, dtype=bool)
    order = np.argsort(-W, axis=1)[:, :k]
    for i in range(ei.N):
        keep[i, order[i]] = True
    keep = keep | keep.T
    Wk = ei.W(w) * keep
    return ei.vec(Wk)


def correlation_weights(Y, ei: EdgeIndex, clip_negative=True):
    """w_ij = max(rho_ij, 0). Negative correlation is *disagreement*: it is set to
    zero, never folded in via |rho|, which would call anti-correlated stations
    strongly connected."""
    R = np.corrcoef(Y)
    r = ei.vec(R)
    return np.maximum(r, 0.0) if clip_negative else r


# --------------------------------------------------------------------------
# C : Kalofolias (AISTATS 2016), eq. (5) in primal form
# --------------------------------------------------------------------------
def kalofolias(Z, ei: EdgeIndex, alpha=1.0, beta=1.0, solver="CLARABEL"):
    """min_w  2 z'w - alpha * sum_i log(deg_i) + beta * ||w||^2,  w >= 0.

    z  : pairwise squared distances between station histories (edge vector)
    The log-degree term forbids isolated nodes; beta controls how concentrated
    the weights are and, with alpha, the overall density.
    """
    import cvxpy as cp
    z = np.asarray(Z, float)
    w = cp.Variable(ei.m, nonneg=True)
    obj = (2.0 * z @ w
           - alpha * cp.sum(cp.log(ei.Sdeg @ w))
           + beta * cp.sum_squares(w))
    prob = cp.Problem(cp.Minimize(obj))
    t0 = time.time()
    prob.solve(solver=solver)
    return dict(w=np.maximum(np.asarray(w.value).ravel(), 0.0),
                status=prob.status, objective=prob.value, seconds=time.time() - t0)


# --------------------------------------------------------------------------
# D : GL-SigRep (Dong et al. 2016)
# --------------------------------------------------------------------------
def gl_sigrep(Y, ei: EdgeIndex, alpha=1.0, beta=0.05, iters=20, tol=1e-6,
              solver="CLARABEL"):
    """min_{L,S} (1/T)[ ||Y-S||_F^2 + alpha tr(S'LS) ] + beta ||L||_F^2 , tr(L)=N.

    Alternates a QP in w (the L-step) with the closed-form S = (I + alpha L)^{-1} Y.
    The 1/T normalisation makes beta comparable across different numbers of days;
    without it the smoothness term grows with T and L collapses onto one edge.
    """
    import cvxpy as cp
    N, T = Y.shape
    Sig = np.array(Y, float)
    hist, w_val = [], None
    t0 = time.time()
    status = None
    for it in range(iters):
        d = ei.pair_distance(Sig @ Sig.T / T)          # tr(L SS')/T  =  d . w
        w = cp.Variable(ei.m, nonneg=True)
        deg = ei.Sdeg @ w
        LF2 = cp.sum_squares(deg) + 2.0 * cp.sum_squares(w)      # ||L||_F^2
        p = cp.Problem(cp.Minimize(alpha * (d @ w) + beta * LF2),
                       [cp.sum(w) == N / 2.0])
        p.solve(solver=solver)
        status = p.status
        w_val = np.maximum(np.asarray(w.value).ravel(), 0.0)
        L = ei.L(w_val)
        Sig = np.linalg.solve(np.eye(N) + alpha * L, Y)
        obj = ((np.sum((Y - Sig) ** 2) + alpha * np.trace(Sig.T @ L @ Sig)) / T
               + beta * np.sum(L ** 2))
        hist.append(obj)
        if it and abs(hist[-2] - hist[-1]) <= tol * abs(hist[-2]):
            break
    return dict(w=w_val, status=status, history=np.array(hist),
                iterations=len(hist), seconds=time.time() - t0, S=Sig)


# --------------------------------------------------------------------------
# E / F : GL-3SR family (Humbert et al., JMLR 2021)
# --------------------------------------------------------------------------
def _U0_complete(n):
    """Eigenbasis of the complete-graph Laplacian; column 0 is the constant vector."""
    L = n * np.eye(n) - np.ones((n, n))
    vals, V = np.linalg.eigh(L)
    V = V[:, np.argsort(vals)]
    return -V if V[0, 0] < 0 else V


def _H_step(U, Y, lbd, alpha, beta, norm="l1"):
    """Row-wise closed forms (Humbert Props. 4-5).

    NOTE: the reference implementation (pierreHmbt/GL-3SR, `solve_H0_closedform`)
    writes `H_new[i:] = ...` where `H_new[i, :] = ...` is meant, so the l0 branch
    overwrites every trailing row. Corrected here.
    """
    UY = U.T @ Y
    nrm = np.linalg.norm(UY, axis=1)
    if norm == "l1":
        shrink = np.where(nrm > beta / 2.0,
                          1.0 - (beta / 2.0) / np.maximum(nrm, 1e-300), 0.0)
    elif norm == "l0":
        shrink = (nrm ** 2 >= beta * (1.0 + alpha * lbd)).astype(float)
    else:
        raise ValueError("norm must be 'l1' or 'l0'")
    return (shrink / (1.0 + alpha * lbd))[:, None] * UY


def _lbd_step(U, H, alpha, N, ei: EdgeIndex, solver="SCS"):
    """min_l alpha * c'l  s.t.  sum l = N, l >= 0, l_1 = 0,
       and (U diag(l) U')_ij <= 0 for every i<j   (valid Laplacian off-diagonals)."""
    import cvxpy as cp
    c = np.sum(H ** 2, axis=1)
    l = cp.Variable(N, nonneg=True)
    A = U[ei.iu[0], :] * U[ei.iu[1], :]
    p = cp.Problem(cp.Minimize(alpha * c @ l),
                   [cp.sum(l) == N, A @ l <= 0, l[0] == 0])
    p.solve(solver=solver)
    lv = np.maximum(np.asarray(l.value).ravel(), 0.0)
    lv[0] = 0.0
    return lv, p.status


def _obj_3sr(Y, U, H, lbd, alpha, beta, norm):
    pen = (np.sum(np.linalg.norm(H, axis=1)) if norm == "l1"
           else float(np.sum(np.linalg.norm(H, axis=1) > 1e-12)))
    return (np.sum((Y - U @ H) ** 2)
            + alpha * np.sum((np.sqrt(lbd)[:, None] * H) ** 2)
            + beta * pen)


def fgl_3sr(Y, ei: EdgeIndex, alpha=1.0, beta=80.0, iters=15, norm="l1",
            tol=1e-4, solver="SCS"):
    """Humbert Algorithm 2 (Fast GL-3SR).

    H : row-wise closed form.  U : orthogonal Procrustes via SVD, keeping the
    constant eigenvector fixed (the *relaxation* -- it drops the Laplacian
    feasibility of U during this step).  lambda : linear program restoring it.
    """
    N = Y.shape[0]
    U0 = _U0_complete(N)
    U = U0.copy()
    lbd = np.full(N, N / (N - 1.0)); lbd[0] = 0.0
    H = np.array(Y, float)
    hist = []
    t0 = time.time()
    status = None
    for it in range(iters):
        H_old = H
        H = _H_step(U, Y, lbd, alpha, beta, norm)
        M = (H @ Y.T @ U0)[1:, 1:]
        P, _, Q = np.linalg.svd(M.T, full_matrices=False)
        R = np.eye(N); R[1:, 1:] = P @ Q
        U = U0 @ R
        lbd, status = _lbd_step(U, H, alpha, N, ei, solver)
        hist.append(_obj_3sr(Y, U, H, lbd, alpha, beta, norm))
        if np.linalg.norm(H - H_old) <= tol * max(np.linalg.norm(H_old), 1e-12):
            break
    L = (U * lbd) @ U.T
    return dict(w=w_from_L(L), L=L, U=U, lbd=lbd, H=H, status=status,
                history=np.array(hist), iterations=len(hist),
                active=int(np.sum(np.linalg.norm(H, axis=1) > 1e-8)),
                seconds=time.time() - t0)


def igl_3sr(Y, ei: EdgeIndex, alpha=1.0, beta=80.0, outer=6, mu0=1.0, mu_decay=0.5,
            cg_iters=40, norm="l1", solver="SCS", seed=0):
    """Humbert Algorithm 1 (Iterative GL-3SR).

    Same H and lambda steps, but U is updated on the orthogonal group with a
    log-barrier keeping every off-diagonal of L = U diag(lambda) U' strictly
    negative, so the iterate stays Laplacian-feasible throughout. Slower than
    FGL-3SR; the barrier weight mu is annealed.
    """
    import pymanopt
    import autograd.numpy as anp
    from pymanopt.manifolds import SpecialOrthogonalGroup
    from pymanopt.optimizers import ConjugateGradient

    N = Y.shape[0]
    U0 = _U0_complete(N)
    manifold = SpecialOrthogonalGroup(N - 1)
    D = np.eye(N - 1)
    lbd = np.full(N, N / (N - 1.0)); lbd[0] = 0.0
    U = U0.copy()
    mu = mu0
    hist, grads, status = [], [], None
    iu = ei.iu
    t0 = time.time()
    for it in range(outer):
        H = _H_step(U, Y, lbd, alpha, beta, norm)
        lbd_c, H_c, mu_c = lbd, H, mu

        @pymanopt.function.autograd(manifold)
        def cost(Dv):
            R = anp.concatenate([
                anp.concatenate([anp.ones((1, 1)), anp.zeros((1, N - 1))], axis=1),
                anp.concatenate([anp.zeros((N - 1, 1)), Dv], axis=1)], axis=0)
            Uv = U0 @ R
            Lv = (Uv * lbd_c) @ Uv.T
            barrier = -mu_c * anp.sum(anp.log(anp.maximum(-Lv[iu], 1e-14)))
            return anp.sum((Y - Uv @ H_c) ** 2) + barrier

        res = ConjugateGradient(max_iterations=cg_iters, verbosity=0).run(
            pymanopt.Problem(manifold, cost), initial_point=D)
        D = res.point
        grads.append(float(res.gradient_norm))
        R = np.eye(N); R[1:, 1:] = D
        U = U0 @ R
        lbd, status = _lbd_step(U, H, alpha, N, ei, solver)
        hist.append(_obj_3sr(Y, U, H, lbd, alpha, beta, norm))
        mu *= mu_decay
    L = (U * lbd) @ U.T
    return dict(w=w_from_L(L), L=L, U=U, lbd=lbd, H=H, status=status,
                history=np.array(hist), gradient_norms=np.array(grads),
                iterations=outer,
                active=int(np.sum(np.linalg.norm(H, axis=1) > 1e-8)),
                seconds=time.time() - t0)


# --------------------------------------------------------------------------
# G : ESA-GL (Sardellitti, Barbarossa & Di Lorenzo 2019)
# --------------------------------------------------------------------------
def esa_gl(Y, ei: EdgeIndex, K=10, iters=25, mu=1e-3, solver="SCS", max_iters=20000):
    """Sardellitti, Barbarossa & Di Lorenzo (2019), in the benchmark form given by
    Humbert et al. as Eqs. 22-23.

    Stage 1 (Eq. 22) -- sparsifying transform learning::

        min_{H,X} ||Y - X H||_F^2   s.t.  X'X = I,  x_1 = 1/sqrt(N) 1,  ||H||_{2,0} <= K

    alternating a hard row-support selection (keep the K highest-energy rows of
    X'Y) with an orthogonal Procrustes update of X that fixes the constant vector.
    No smoothness term appears here; that is the method's structural difference
    from GL-3SR.

    Stage 2 (Eq. 23) -- topology recovery::

        min_{L,C_K}  tr(H_K' C_K H_K) + mu ||L||_F^2
        s.t.  L X_K = X_K C_K,  C_K >= 0,  L a valid Laplacian,  tr(L) = N

    **The first term is essential and easy to drop by accident.** With C_K playing
    the role of the eigenvalues restricted to the active subspace,
    tr(H_K' C_K H_K) = tr(C_K H_K H_K') is the Dirichlet energy of the learned
    representation, and it is the only thing pushing the active modes to LOW graph
    frequency. Omit it -- e.g. by minimising the invariance residual with a ridge
    instead -- and the uniform complete graph becomes optimal: every vector
    orthogonal to 1 is then an eigenvector with the same eigenvalue, so
    L X_K = X_K C_K holds for *any* X_K with C_K = lambda I, at zero residual and
    minimum norm. The result is a flat spectrum that carries no information.
    """
    import cvxpy as cp
    import scipy.sparse as sp

    N = Y.shape[0]
    t0 = time.time()

    # ---- stage 1 -------------------------------------------------------------
    U0 = _U0_complete(N)
    U = U0.copy()
    keep = None
    for _ in range(iters):
        A = U.T @ Y
        keep = np.argsort(-np.sum(A ** 2, axis=1))[:K]
        H = np.zeros_like(A)
        H[keep] = A[keep]
        M = (H @ Y.T @ U0)[1:, 1:]
        P, _, Q = np.linalg.svd(M.T, full_matrices=False)
        R = np.eye(N); R[1:, 1:] = P @ Q
        U = U0 @ R
    keep = np.sort(keep)
    XK = U[:, keep]                      # N x K active subspace
    HK = (U.T @ Y)[keep]                 # K x T active coefficients
    GK = HK @ HK.T                       # K x K, constant in the SDP

    # ---- stage 2 -------------------------------------------------------------
    # (L(w) X_K)[:, c] = Dc[c] @ w, so the invariance is a linear equality in w.
    maps = ei.neighbour_map(XK)
    Dc = [sp.diags(XK[:, c]) @ ei.Sdeg - maps[c] for c in range(K)]

    w = cp.Variable(ei.m, nonneg=True)          # Laplacian validity is structural
    C = cp.Variable((K, K), PSD=True)
    deg = ei.Sdeg @ w
    LF2 = cp.sum_squares(deg) + 2.0 * cp.sum_squares(w)      # ||L||_F^2
    cons = [cp.sum(w) == N / 2.0]                            # tr(L) = N
    for c in range(K):
        cons.append(Dc[c] @ w == XK @ C[:, c])               # L X_K = X_K C_K
    prob = cp.Problem(cp.Minimize(cp.trace(C @ GK) + mu * LF2), cons)
    prob.solve(solver=solver, max_iters=max_iters)

    wv = np.maximum(np.asarray(w.value).ravel(), 0.0)
    Cv = np.asarray(C.value)
    L = ei.L(wv)
    return dict(w=wv, U=U, active_modes=keep, C=Cv,
                smoothness=float(np.trace(Cv @ GK)),
                residual=float(np.linalg.norm(L @ XK - XK @ Cv)),
                status=prob.status, objective=prob.value, seconds=time.time() - t0)
