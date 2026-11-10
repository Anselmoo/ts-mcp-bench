import numpy as np, itertools, scipy.special as sp
def sph(l,m,th,ph):
    if hasattr(sp,'sph_harm_y'): return sp.sph_harm_y(l,m,th,ph)
    return sp.sph_harm(m,l,ph,th)
xg, wg = np.polynomial.legendre.leggauss(16)
phis = np.linspace(0, 2*np.pi, 32, endpoint=False); wp = 2*np.pi/32
TH, PH = np.meshgrid(np.arccos(xg), phis, indexing='ij')
W = np.outer(wg, np.full(len(phis), wp))
def integ(f): return np.sum(W*f)
ms=list(range(-2,3))
Yc_={ (l,m): sph(l,m,TH,PH) for l in (2,4) for m in range(-l,l+1)}
def ang(k):
    A=np.zeros((5,5,5,5),complex)
    for i1,m1 in enumerate(ms):
     for i3,m3 in enumerate(ms):
      for q in range(-k,k+1):
        Ykq=Yc_[(k,q)]
        a=integ(np.conj(Yc_[(2,m1)])*Yc_[(2,m3)]*np.conj(Ykq))
        if abs(a)<1e-14: continue
        for i2,m2 in enumerate(ms):
         for i4,m4 in enumerate(ms):
            b=integ(np.conj(Yc_[(2,m2)])*Yc_[(2,m4)]*Ykq)
            A[i1,i2,i3,i4]+=4*np.pi/(2*k+1)*a*b
    return A
A={k:ang(k) for k in (2,4)}
A[0]=None
X=np.sin(TH)*np.cos(PH); Yy=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
def pv(fs):
    out=[]
    for f in fs:
        v=np.array([integ(np.conj(Yc_[(2,m)])*f) for m in ms])
        for u in out: v=v-np.vdot(u,v)*u
        out.append(v/np.linalg.norm(v))
    return out
def pr(vs):
    P=np.zeros((5,5),complex)
    for v in vs: P+=np.outer(np.conj(v),v)
    return P
Pt2=pr(pv([X*Yy,Yy*Z,X*Z])); Pe=pr(pv([X**2-Yy**2,3*Z**2-1]))
print("traces",np.trace(Pt2).real,np.trace(Pe).real)
hcf=-4*Pt2+6*Pe
basis=list(itertools.combinations(range(5),2)); idx={b:i for i,b in enumerate(basis)}
def apply(ops,st):
    st=list(st); sg=1
    for typ,o in reversed(ops):
        n=sum(1 for x in st if x<o)
        if typ=='c':
            if o in st: return None,0
            sg*=(-1)**n; st=sorted(st+[o])
        else:
            if o not in st: return None,0
            sg*=(-1)**n; st.remove(o)
    return tuple(st),sg
def Hmat(Dq,B,C=None):
    if C is None: C=4*B
    F4=441*C/35; F2=(441*B+5*F4)/9
    Vm=F2*A[2]+F4*A[4]
    H=np.zeros((10,10),complex)
    for J,st in enumerate(basis):
        for a in range(5):
          for b in range(5):
            if abs(hcf[a,b])>1e-12:
              r,s=apply([('c',a),('a',b)],st)
              if r is not None and len(r)==2: H[idx[r],J]+=Dq*hcf[a,b]*s
        for a,b,c,d in itertools.product(range(5),repeat=4):
            v=Vm[a,b,c,d]
            if abs(v)<1e-12: continue
            r,s=apply([('c',a),('c',b),('a',d),('a',c)],st)
            if r is not None and len(r)==2: H[idx[r],J]+=0.5*v*s
    return H
print("free ion Ms=1 (B=1,C=4):",np.round(np.linalg.eigvalsh(Hmat(0,1.0)),4))
print("free ion Ms=1 (B=1,C=0):",np.round(np.linalg.eigvalsh(Hmat(0,1.0,C=0.0)),4))
