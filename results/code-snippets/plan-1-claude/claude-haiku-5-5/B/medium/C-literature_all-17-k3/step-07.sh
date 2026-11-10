python3 - <<'EOF'
import numpy as np
from scipy.special import lpmv, factorial
from scipy.optimize import least_squares
xg,wg=np.polynomial.legendre.leggauss(30)
phis=np.linspace(0,2*np.pi,60,endpoint=False); wp=2*np.pi/60
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij'); W=(wg[:,None]*wp*np.ones_like(TH))
def Y(l,m,th,ph):
    am=abs(m); N=np.sqrt((2*l+1)/(4*np.pi)*factorial(l-am)/factorial(l+am))
    y=N*lpmv(am,l,np.cos(th))*np.exp(1j*am*ph)
    if m<0: y=(-1)**am*np.conj(y)
    return y
ms=[-2,-1,0,1,2]
Yd={m:Y(2,m,TH,PH) for m in ms}
Ang={}
for k in (0,2,4):
    for a in ms:
        for c in ms:
            for q in range(-k,k+1):
                Ang[(a,c,k,q)]=np.sum(W*np.conj(Yd[a])*Yd[c]*np.conj(Y(k,q,TH,PH)))
def Vspat(a,b,c,d,F):
    tot=0
    for k in (0,2,4):
        s=sum(Ang[(a,c,k,q)]*Ang[(b,d,k,-q)]*(-1)**q for q in range(-k,k+1))
        tot+=F[k]*4*np.pi/(2*k+1)*s
    return tot
so=[(m,s) for m in ms for s in (0,1)]
states=[x for x in range(1024) if bin(x).count('1')==8]
idx={x:i for i,x in enumerate(states)}; D=len(states)
def op(ops):
    M=np.zeros((D,D))
    for x in states:
        y=x; s=1; ok=True
        for typ,i in reversed(ops):
            nb=bin(y&((1<<i)-1)).count('1')
            if typ=='c':
                if not (y>>i)&1: ok=False;break
                y^=(1<<i); s*=(-1)**nb
            else:
                if (y>>i)&1: ok=False;break
                y|=(1<<i); s*=(-1)**nb
        if ok and y in idx: M[idx[y],idx[x]]+=s
    return M
Sp=sum(op([('a',2*m),('c',2*m+1)]) for m in range(5))
Sz=sum(0.5*(op([('a',2*m),('c',2*m)])-op([('a',2*m+1),('c',2*m+1)])) for m in range(5))
S2=Sp.T@Sp+Sz@Sz+Sz
# precompute two-body operator pieces (Dq,B,C independent) as linear combos of F2,F4
pieces=[]  # (a,b,c,d, angular coefficient vector for k=0,2,4 part, matrix)
Mops={}
for a in range(10):
    for b in range(10):
        for c in range(10):
            for d in range(10):
                ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
                if sa!=sc or sb!=sd or a==b or c==d: continue
                coef=[]
                for k in (2,4):
                    s=sum(Ang[(ma,mc,k,q)]*Ang[(mb,md,k,-q)]*(-1)**q for q in range(-k,k+1))
                    coef.append(4*np.pi/(2*k+1)*s)
                if max(abs(x) for x in coef)<1e-12: continue
                Mops[(a,b,c,d)]=(np.array(coef),op([('a',a),('a',b),('c',d),('c',c)]))
one={}
for i in range(10):
  for j in range(10):
    if so[i][1]==so[j][1]: one[(i,j)]=op([('a',i),('c',j)])
def spectrum(Dq,B,C):
    F2=49*B+7*C; F4=441*C/35
    s2=np.sqrt(2)
    def vec(d):
        v=np.zeros(5,complex)
        for m,c in d.items(): v[m+2]=c
        return v
    eg=[vec({0:1}),vec({2:1/s2,-2:1/s2})]
    t2=[vec({1:-1/s2,-1:1/s2}),vec({1:-1j/s2,-1:-1j/s2}),vec({2:-1j/s2,-2:1j/s2})]
    P=sum(6*Dq*np.outer(v,v.conj()) for v in eg)+sum(-4*Dq*np.outer(v,v.conj()) for v in t2)
    H=np.zeros((D,D),complex)
    for i in range(10):
        for j in range(10):
            if (i,j) in one and abs(P[so[i][0]+2,so[j][0]+2])>1e-14:
                H+=P[so[i][0]+2,so[j][0]+2]*one[(i,j)]
    for key,(coef,M) in Mops.items():
        H+=0.5*(coef[0]*F2+coef[1]*F4)*M
    return H
def levels(Dq,B,C):
    H=spectrum(Dq,B,C)
    Hm=H+1e6*(S2-2*np.eye(D))@(S2-2*np.eye(D))  # force S=1
    w,v=np.linalg.eigh(Hm)
    trip=np.round(w[np.abs(w-w.min())<=1e5 if False else np.arange(D)],6)
    # keep S=1 eigenvalues (those with Hm eigen ~ H eigen)
    out=[]
    Pm=np.abs(v)**2
    for k in range(D):
        if abs(w[k]-np.round(w[k]))>=0 and w[k]<5e5:
            out.append(w[k])
    return np.array(out)
def triplet_singlet(Dq,B,C):
    H=spectrum(Dq,B,C)
    T=H+1e6*(S2-2*np.eye(D))@(S2-2*np.eye(D))
    wt=np.linalg.eigvalsh(T); wt=wt[wt<5e5]
    Sg=H+1e6*(S2)@(S2)  # dummy
    S0=H+1e6*(S2@S2)
    ws=np.linalg.eigvalsh(H+1e6*S2@S2); ws=ws[ws<5e5]
    return wt,ws
wt,ws=triplet_singlet(0.0,1000,4000)
print("n triplets",len(wt),"n singlets",len(ws))
print(np.round(wt-wt[0],0)[:40])
print(np.round(ws-wt[0],0))
EOF