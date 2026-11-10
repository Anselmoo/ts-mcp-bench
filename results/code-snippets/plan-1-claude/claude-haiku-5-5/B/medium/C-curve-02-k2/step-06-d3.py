import numpy as np, itertools
from scipy.special import sph_harm
from scipy.linalg import expm
from numpy.polynomial.legendre import leggauss

B = 1.0
C = 3003/722.0
F4 = (441/35.0)*C
F2 = 49*B + 5*F4/9.0
F0 = 0.0
l=2; ms=list(range(-2,3)); n=10
def so(i,s): return 2*i+s
xg,wg = leggauss(30); nphi=48
phis=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij')
W=(wg[:,None]*np.ones((1,nphi)))*(2*np.pi/nphi)
def Yf(l_,m_): return sph_harm(m_,l_,PH,TH)
Ylm={m:Yf(2,m) for m in ms}
M={}
for k in (0,2,4):
    arr=np.zeros((5,5,2*k+1),complex)
    for ia,ma in enumerate(ms):
        for ic,mc in enumerate(ms):
            for iq,q in enumerate(range(-k,k+1)):
                Ykq=Yf(k,q)
                arr[ia,ic,iq]=np.sum(W*np.conj(Ylm[ma])*Ylm[mc]*np.conj(Ykq))
    M[k]=arr
Fk={0:F0,2:F2,4:F4}
def angular(k,a,c,b,d):
    s=sum(M[k][a,c,iq]*np.conj(M[k][d,b,iq]) for iq in range(2*k+1))
    return 4*np.pi/(2*k+1)*s
V=np.zeros((5,5,5,5),complex)
for a in range(5):
 for b in range(5):
  for c in range(5):
   for d in range(5):
    V[a,b,c,d]=sum(Fk[k]*angular(k,a,c,b,d) for k in (0,2,4))
Vso=np.zeros((n,n,n,n),complex)
for i in range(5):
 for j in range(5):
  for k_ in range(5):
   for m_ in range(5):
    for s in range(2):
     for t in range(2):
      Vso[so(i,s),so(j,t),so(k_,s),so(m_,t)]=V[i,j,k_,m_]
dets=list(itertools.combinations(range(n),3))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(ops,det):
    occ=list(det); sign=1
    for typ,p in ops:
        if typ=='a':
            if p not in occ: return None,0
            pos=occ.index(p); sign*=(-1)**pos; occ.pop(pos)
        else:
            if p in occ: return None,0
            pos=sum(1 for x in occ if x<p); sign*=(-1)**pos; occ.insert(pos,p)
    return tuple(occ),sign
def build_Hee():
    H=np.zeros((len(dets),len(dets)),complex)
    for I,dt in enumerate(dets):
        for a,b,c,d in itertools.product(range(n),repeat=4):
            v=Vso[a,b,c,d]
            if abs(v)<1e-14: continue
            new,s=apply_ops([('a',c),('a',d),('c',b),('c',a)],dt)
            if new is None: continue
            H[idx[new],I]+=0.5*v*s
    return H
def build_H1(h10):
    H=np.zeros((len(dets),len(dets)),complex)
    for I,dt in enumerate(dets):
        for a in range(n):
            for b in range(n):
                v=h10[a,b]
                if abs(v)<1e-14: continue
                new,s=apply_ops([('a',b),('c',a)],dt)
                if new is None: continue
                H[idx[new],I]+=v*s
    return H
Hee=build_Hee()
Lp=np.zeros((5,5),complex)
for i,m in enumerate(ms):
    if m<2: Lp[i+1,i]=np.sqrt(l*(l+1)-m*(m+1))
Lm=Lp.conj().T
Lx=(Lp+Lm)/2; Ly=(Lp-Lm)/(2j); Lz=np.diag(ms).astype(complex)
def Drot(axis,theta):
    ax=np.array(axis,float); ax/=np.linalg.norm(ax)
    return expm(-1j*theta*(ax[0]*Lx+ax[1]*Ly+ax[2]*Lz))
def lam3(g5):
    g=np.kron(g5,np.eye(2))
    G=np.zeros((len(dets),len(dets)),complex)
    for J,dj in enumerate(dets):
        for I,di in enumerate(dets):
            G[I,J]=np.linalg.det(g[np.ix_(di,dj)])
    return G
cls=['E','8C3','3C2','6C4','6C2p']
csize={'E':1,'8C3':8,'3C2':3,'6C4':6,'6C2p':6}
grp={'E':np.eye(5),'8C3':Drot([1,1,1],2*np.pi/3),'3C2':Drot([0,0,1],np.pi),
     '6C4':Drot([0,0,1],np.pi/2),'6C2p':Drot([1,1,0],np.pi)}
Lam={c:lam3(grp[c]) for c in cls}
chartab={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
def nup(d): return sum(1 for p in d if p%2==0)
sec32=[i for i,d in enumerate(dets) if nup(d)==3]
sec12=[i for i,d in enumerate(dets) if nup(d)==2]
def decompose(chi):
    out={}
    for name,row in chartab.items():
        s=sum(csize[c]*chi[j]*row[j] for j,c in enumerate(cls))/120.0
        if abs(s)>1e-6: out[name]=round(s.real,3)
    return out
def clusters(evals,tol=1e-6):
    groups=[]
    for i,e in enumerate(evals):
        if groups and abs(e-groups[-1][0])<tol: groups[-1][1].append(i)
        else: groups.append([e,[i]])
    return groups
def run(Dq):
    Peg=np.zeros((5,5),complex)
    for v in [np.eye(5)[ms.index(0)], (np.eye(5)[ms.index(2)]+np.eye(5)[ms.index(-2)])/np.sqrt(2)]:
        Peg+=np.outer(v,v.conj())
    Pt2=np.eye(5)-Peg
    h10=np.kron(6*Dq*Peg-4*Dq*Pt2,np.eye(2))
    H=Hee+build_H1(h10)
    def sector(secidx):
        Hs=H[np.ix_(secidx,secidx)]
        ev,U=np.linalg.eigh(Hs)
        Ufull=np.zeros((len(dets),len(ev)),complex); Ufull[secidx,:]=U
        out=[]
        for e,cl in clusters(ev):
            Vc=Ufull[:,cl]
            chi=np.array([np.trace(Vc.conj().T@Lam[c]@Vc) for c in cls])
            out.append((e,len(cl),chi))
        return out
    q=sector(sec32); d=sector(sec12)
    E0=q[0][0]
    quart=[(e-E0,m,chi) for e,m,chi in q]
    dbl=[]
    for e,m,chi in d:
        qmatch=[c for ee,mm,c in q if abs(ee-e)<1e-6]
        if qmatch: chi=chi-qmatch[0]
        mm=round(chi[0].real)
        if mm>0: dbl.append((e-E0,mm,chi))
    return quart,dbl
if __name__=='__main__':
    for Dq in [1.0,2.2,3.5]:
        quart,dbl=run(Dq)
        print("Dq/B=",Dq)
        terms=[(e,'4',m,decompose(c)) for e,m,c in quart]+[(e,'2',m,decompose(c)) for e,m,c in dbl]
        for t in sorted(terms,key=lambda x:x[0]):
            print("  E=%.4f  mult=%d  S=%s  %s"%(t[0],t[2],t[1],t[3]))
