mkdir -p /tmp/w && cd /tmp/w && cat > ts.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y, eval_legendre
nt, nphi = 30, 60
x, wx = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = (np.repeat(wx[:,None],nphi,1))*(2*np.pi/nphi)
ms = [-2,-1,0,1,2]
def Y(l,m,T,P): return sph_harm_y(l,m,T,P)
Ylm = {m: Y(2,m,TH,PH) for m in ms}
dirs = np.array([[0,0,1],[0,0,-1],[1,0,0],[-1,0,0],[0,1,0],[0,-1,0]],float)
rx = np.sin(TH)*np.cos(PH); ry=np.sin(TH)*np.sin(PH); rz=np.cos(TH)
V0 = np.zeros_like(TH)
for d in dirs:
    V0 += eval_legendre(4, rx*d[0]+ry*d[1]+rz*d[2])
def integ(f): return np.sum(W*f)
h1 = np.zeros((5,5),complex)
for a,ma in enumerate(ms):
    for c,mc in enumerate(ms):
        h1[a,c] = integ(np.conj(Ylm[ma])*V0*Ylm[mc])
ev = np.linalg.eigvalsh(h1)
print("unit eig", np.round(ev,6))
# t2g = lowest 3, eg = top 2
gap = ev[3]-ev[1]
print("gap", gap)
h1 = h1.real*10/gap   # eg - t2g = 10 Dq, Dq=1 ; t2g at -4, eg at +6 after shift
ev2=np.linalg.eigvalsh(h1); print("scaled", np.round(ev2,4))
Ang={}; Ang2={}
for k in [0,2,4]:
    M=np.zeros((5,5,2*k+1),complex); N=np.zeros((5,5,2*k+1),complex)
    for qi,q in enumerate(range(-k,k+1)):
        Ykq=Y(k,q,TH,PH)
        for a,ma in enumerate(ms):
            for c,mc in enumerate(ms):
                M[a,c,qi]=integ(np.conj(Ylm[ma])*Ylm[mc]*np.conj(Ykq))
                N[a,c,qi]=integ(np.conj(Ylm[ma])*Ylm[mc]*Ykq)
    Ang[k]=M; Ang2[k]=N
def Aang(k,a,c,b,d):
    return (4*np.pi/(2*k+1))*np.sum(Ang[k][a,c,:]*Ang2[k][b,d,:])
def coul_tensor(F2,F4):
    Fk={0:0.0,2:F2,4:F4}
    V=np.zeros((5,5,5,5))
    for a in range(5):
     for c in range(5):
      for b in range(5):
       for d in range(5):
        V[a,c,b,d]=sum(Fk[k]*Aang(k,a,c,b,d).real for k in [2,4])
    return V
def so(o,s): return 2*o+s
def build_basis(nup,ndn):
    dets=[]
    for up in itertools.combinations(range(5),nup):
        for dn in itertools.combinations(range(5),ndn):
            dets.append(tuple(sorted([so(o,0) for o in up]+[so(o,1) for o in dn])))
    return dets
def apply_c(occ,i,cr):
    occ=list(occ)
    if cr:
        if i in occ: return None
        pos=sum(1 for x in occ if x<i); occ.append(i); occ.sort(); return ((-1)**pos,tuple(occ))
    else:
        if i not in occ: return None
        pos=occ.index(i); occ.pop(pos); return ((-1)**pos,tuple(occ))
def apply_seq(occ,ops):
    sign=1; cur=occ
    for (i,cr) in reversed(ops):
        r=apply_c(cur,i,cr)
        if r is None: return None
        sign*=r[0]; cur=r[1]
    return sign,cur
def hamiltonian(dets,h1,V):
    idx={d:n for n,d in enumerate(dets)}
    H=np.zeros((len(dets),len(dets)))
    for n,occ in enumerate(dets):
        for a in range(5):
          for c in range(5):
            if abs(h1[a,c])<1e-14: continue
            for s in range(2):
              r=apply_seq(occ,[(so(a,s),True),(so(c,s),False)])
              if r is None: continue
              H[idx[r[1]],n]+=r[0]*h1[a,c]
        for a in range(5):
         for b in range(5):
          for c in range(5):
           for d in range(5):
            v=V[a,c,b,d]
            if abs(v)<1e-14: continue
            for s1 in range(2):
             for s2 in range(2):
              r=apply_seq(occ,[(so(a,s1),True),(so(b,s2),True),(so(d,s2),False),(so(c,s1),False)])
              if r is None: continue
              H[idx[r[1]],n]+=0.5*r[0]*v
    return H
def levels(Dq,B,C_over_B=4.5):
    x=9*C_over_B/(35+45*C_over_B)   # F4/F2
    # B=(F2-5F4)/49 -> F2 = 49B + 5F4 ; F4 = x F2  => F2 = 49B/(1-5x)
    F2=49*B/(1-5*x); F4=x*F2
    V=coul_tensor(F2,F4)
    H=hamiltonian(build_basis(5,3),Dq*h1,V)
    e=np.linalg.eigvalsh(H)
    return e
EOF
python3 -c "
import ts, numpy as np
e=ts.levels(0,1000)
print(len(e)); print(np.round(e,3))
"