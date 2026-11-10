import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
l=2; ms=[-2,-1,0,1,2]
# c^k(m1,m2)
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*(2*l+1)*gaunt(l,k,l,-m1,m1-m2,m2)) if abs(m1-m2)<=k else 0.0
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
dets=[c for c in itertools.combinations(range(10),7)]
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def two(F):  # F dict k->Fk
    V={}
    for a in range(10):
     for b in range(10):
      for c in range(10):
       for d in range(10):
        ma,sa=so[a];mb,sb=so[b];mc,sc=so[c];md,sd=so[d]
        if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
        v=sum(F[k]*CK[(k,ma,mc)]*CK[(k,md,mb)] for k in (0,2,4))
        if v: V[(a,b,c,d)]=v
    return V
def apply_ops(det,ops):
    # ops list of (type,orb) applied right to left; returns sign,newdet or None
    st=list(det); sgn=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in st: return None
            p=st.index(o); sgn*=(-1)**p; st.pop(p)
        else:
            if o in st: return None
            p=sum(1 for x in st if x<o); sgn*=(-1)**p; st.insert(p,o)
    return sgn,tuple(st)
def build_two(V):
    H=np.zeros((N,N))
    for j,d in enumerate(dets):
        for (a,b,c,dd),v in V.items():
            r=apply_ops(d,[('c',a),('c',b),('a',dd),('a',c)])
            if r: H[idx[r[1]],j]+=0.5*v
    return H
def build_one(h):
    H=np.zeros((N,N))
    for j,d in enumerate(dets):
        for a in range(10):
            for b in range(10):
                if h[a,b]==0: continue
                r=apply_ops(d,[('c',a),('a',b)])
                if r: H[idx[r[1]],j]+=r[0]*h[a,b]
    return H
# Racah: F0 irrelevant, F2=49F2', B=F2'-5F4', C=35F4'
VF2=build_two(two({0:0,2:1,4:0})); VF4=build_two(two({0:0,2:0,4:1}))
# crystal field octahedral in complex basis: V = Dq*(6 for m=0, -4 m=±1, 1 m=±2, and 5 between ±2? standard)
h=np.zeros((5,5)); M={m:i for i,m in enumerate(ms)}
h[M[0],M[0]]=6; h[M[1],M[1]]=h[M[-1],M[-1]]=-4; h[M[2],M[2]]=h[M[-2],M[-2]]=1; h[M[2],M[-2]]=h[M[-2],M[2]]=5
hs=np.zeros((10,10))
for a in range(10):
    for b in range(10):
        if so[a][1]==so[b][1]: hs[a,b]=h[M[so[a][0]],M[so[b][0]]]
HCF=build_one(hs)
# Sz, S^2
Sz=np.array([sum(0.5 if so[o][1]==0 else -0.5 for o in d) for d in dets])
splus=np.zeros((10,10))
for a in range(10):
    for b in range(10):
        if so[a][0]==so[b][0] and so[a][1]==0 and so[b][1]==1: splus[a,b]=1
Sp=build_one(splus); S2=Sp.T@Sp+np.diag(Sz**2+Sz)
# C4 about z: d_m -> e^{i m pi/2} d_m (complex basis), trace of diagonal
c4=np.array([sum(so[o][0] for o in d)%4 for d in dets])
c4ph=np.exp(1j*np.pi/2*c4)
sel=np.where(np.isclose(Sz,0.5))[0]
def levels(Dq,B,C):
    F4=C/35; F2=B+5*F4
    H=F2*VF2+F4*VF4+Dq*HCF
    Hs=H[np.ix_(sel,sel)]; S2s=S2[np.ix_(sel,sel)]
    Hs=Hs+1e-6*S2s
    w,v=np.linalg.eigh(Hs)
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        vv=v[:,i:j]; S=np.real(np.trace(vv.T@S2s@vv))/(j-i)
        tr=np.real(np.sum(np.abs(vv)**2*c4ph[sel][:,None]))
        deg=j-i; Sval=round((-1+np.sqrt(1+4*S))/2*2)/2
        lab={1:{1:'A1',-1:'A2'},2:{0:'E'},3:{1:'T1',-1:'T2'}}[deg][int(round(tr))]
        out.append((w[i],2*Sval+1,lab)); i=j
    E0=out[0][0]
    return [(e-E0,int(m),l) for e,m,l in out]
def pick(L,m,l,n):
    return [e for e,mm,ll in L if mm==m and ll==l][n-1]
obs=np.array([7150,15200,19200,21130])
def res(p):
    L=levels(*p)
    return np.array([pick(L,4,'T2',1),pick(L,4,'A2',1),pick(L,4,'T1',2),pick(L,2,'T1',2)])-obs
print(levels(805,850,3800)[:12])
r=least_squares(res,[805,850,3800]);print(r.x,res(r.x))
