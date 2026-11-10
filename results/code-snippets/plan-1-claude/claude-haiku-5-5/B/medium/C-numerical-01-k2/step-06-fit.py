import numpy as np, itertools
from scipy.optimize import least_squares
d=np.load('ops.npz'); M2,M4,Wc,ev=d['M2'],d['M4'],d['Wc'],d['ev']
so=[(m,s) for m in range(-2,3) for s in (1,-1)]; N=len(so)
states=list(itertools.combinations(range(N),2)); idx={s:i for i,s in enumerate(states)}
# one-electron operator matrix in spin orbitals (in units of Dq): h = 24.8 * Wc (t2g=-4, eg=+6)
scale=-4/ev[0]
def h1_2e():
    M=np.zeros((len(states),len(states)),dtype=complex)
    for ci,s in enumerate(states):
        for i in range(N):
            for j in range(N):
                mi,si=so[i]; mj,sj=so[j]
                if si!=sj: continue
                h=scale*Wc[mi+2,mj+2]
                if abs(h)<1e-14: continue
                # a†_i a_j
                occ=list(s); sign=1
                if j not in occ: continue
                p=occ.index(j); sign*=(-1)**p; occ.pop(p)
                if i in occ: continue
                p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
                M[idx[tuple(occ)],ci]+=h*sign
    return M
H1=h1_2e()
# restrict to M_S=1 (both spins up) for triplet states
up=[i for i,(m,s) in enumerate(so) if s==1]
tri=[idx[s] for s in states if all(so[x][1]==1 for x in s)]
def spectrum(Dq,B,C):
    F4=12.6*C; F2=(441*B+5*F4)/9
    H=Dq*H1+F2*M2+F4*M4
    Ht=H[np.ix_(tri,tri)]
    e=np.linalg.eigvalsh((Ht+Ht.conj().T)/2)
    return np.real(e)
import sys
# sanity: Dq=1,B=0,C=0 gives t2^2 config energies
print(np.round(spectrum(1,0,0),4))
print(np.round(spectrum(0,1,0),4))
