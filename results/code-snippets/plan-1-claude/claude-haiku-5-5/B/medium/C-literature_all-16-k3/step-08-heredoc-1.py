import numpy as np
from scipy.special import sph_harm_y as SY
from scipy.optimize import least_squares
nth, nph = 30, 60
x, w = np.polynomial.legendre.leggauss(nth)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.ones(nph))*(2*np.pi/nph)
ms = list(range(-2,3))
Ylm = {m: SY(2,m,TH,PH) for m in ms}
def ang_k(k):
    A = np.zeros((5,5,5,5), complex)
    for q in range(-k,k+1):
        Yq = SY(k,q,TH,PH)
        P1 = np.array([[np.sum(W*np.conj(Ylm[a])*np.conj(Yq)*Ylm[c]) for c in ms] for a in ms])
        P2 = np.array([[np.sum(W*np.conj(Ylm[b])*Yq*Ylm[d]) for d in ms] for b in ms])
        A += (4*np.pi/(2*k+1))*np.einsum('ac,bd->abcd', P1, P2)
    return A.real
A0,A2,A4 = ang_k(0),ang_k(2),ang_k(4)
s2=np.sqrt(2)
states = [st for st in range(1<<10) if bin(st).count('1')==8]
index = {st:i for i,st in enumerate(states)}
n=len(states)
def ann(i,st):
    if not (st>>i)&1: return None
    return (-1)**bin(st & ((1<<i)-1)).count('1'), st ^ (1<<i)
def cre(i,st):
    if (st>>i)&1: return None
    return (-1)**bin(st & ((1<<i)-1)).count('1'), st | (1<<i)
def op2(a,b,c,d):  # c+_a c+_b c_d c_c
    M = np.zeros((n,n))
    for st in states:
        r=ann(c,st)
        if r is None: continue
        s1,t=r; r=ann(d,t)
        if r is None: continue
        s2,t=r; r=cre(b,t)
        if r is None: continue
        s3,t=r; r=cre(a,t)
        if r is None: continue
        s4,t=r
        M[index[t],index[st]] += s1*s2*s3*s4
    return M
def so(o,s): return 2*o+s
# two-body: H_ee = 1/2 sum V_abcd sum_{s,t} c+_{a s} c+_{b t} c_{d t} c_{c s}
# Matrix elements of the operator for each F-type
pairs = [(a,b,c,d) for a in range(5) for b in range(5) for c in range(5) for d in range(5)]
ops = {}
def getop(a,b,c,d,s,t):
    k=(a,b,c,d,s,t)
    if k not in ops: ops[k]=op2(so(a,s),so(b,t),so(d,t),so(c,s))
    return ops[k]
HF = {'F0':np.zeros((n,n)),'F2':np.zeros((n,n)),'F4':np.zeros((n,n))}
for (a,b,c,d) in pairs:
    for key,Amat in (('F0',A0),('F2',A2),('F4',A4)):
        v=Amat[a,b,c,d]
        if abs(v)<1e-12: continue
        for s in (0,1):
            for t in (0,1):
                HF[key] += 0.5*v*getop(a,b,c,d,s,t)
# one-body: h_ab c+_a c_b  for orbital matrix hm
def one(a,b):
    M=np.zeros((n,n))
    for s in (0,1):
        for st in states:
            r=ann(so(b,s),st)
            if r is None: continue
            s1,t=r; r=cre(so(a,s),t)
            if r is None: continue
            s2,t=r
            M[index[t],index[st]] += s1*s2
    return M
ONE = {(a,b):one(a,b) for a in range(5) for b in range(5)}
v_xy = np.zeros(5,complex); v_xy[4]=1/(1j*s2); v_xy[0]=-1/(1j*s2)
v_xz = np.zeros(5,complex); v_xz[3]=-1/s2; v_xz[1]=1/s2
v_yz = np.zeros(5,complex); v_yz[3]=1j/s2; v_yz[1]=1j/s2
v_z2 = np.zeros(5,complex); v_z2[2]=1
v_x2 = np.zeros(5,complex); v_x2[4]=1/s2; v_x2[0]=1/s2
Pt = sum(np.outer(v,v.conj()) for v in (v_xy,v_xz,v_yz))
Pe = sum(np.outer(v,v.conj()) for v in (v_z2,v_x2))
print("proj check", np.allclose(Pt@Pt,Pt), np.allclose(Pe@Pe,Pe), np.allclose(Pt+Pe,np.eye(5)))
def Hfull(Dq,B,C):
    F4=12.6*C; F2=49*B+7*C
    hm = -4*Dq*Pt + 6*Dq*Pe
    H = F2*HF['F2']+F4*HF['F4']
    for a in range(5):
        for b in range(5):
            if abs(hm[a,b])>1e-14: H = H + hm[a,b]*ONE[(a,b)]
    return H
# Sz sectors
Sz = np.array([sum(((st>>(2*o))&1)-((st>>(2*o+1))&1) for o in range(5)) for st in states])
def spec(Dq,B,C):
    H = Hfull(Dq,B,C)
    iz = np.where(Sz==2)[0]
    et = np.sort(np.linalg.eigvalsh(H[np.ix_(iz,iz)]))
    i0 = np.where(Sz==0)[0]
    ez = list(np.sort(np.linalg.eigvalsh(H[np.ix_(i0,i0)])))
    for t in et:
        j=int(np.argmin(np.abs(np.array(ez)-t))); ez.pop(j)
    return et, np.array(ez), H
# free-ion check: Dq=0 -> levels relative to ground
et,ez,H = spec(0,1000,4000)
print("Hermitian:", np.allclose(H,H.T))
print("triplets:", np.round(et-et[0],1))
print("singlets:", np.round(ez-et[0],1))
