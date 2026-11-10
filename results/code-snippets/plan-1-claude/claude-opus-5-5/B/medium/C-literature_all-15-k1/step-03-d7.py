import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    return float((-1)**m1*5*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2)) if abs(m1-m2)<=k else 0.
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def g(a,b,c,d,F):
    if a[1]!=c[1] or b[1]!=d[1] or a[0]+b[0]!=c[0]+d[0]: return 0
    return sum(F[k]*C[(k,a[0],c[0])]*C[(k,d[0],b[0])] for k in (0,2,4))
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def apply(D,ann,cre):
    L=list(D); sign=1
    for o in ann:
        if o not in L: return None,0
        k=L.index(o); sign*=(-1)**k; L.pop(k)
    for o in cre:
        if o in L: return None,0
        k=sum(1 for x in L if x<o); sign*=(-1)**k; L.insert(k,o)
    return tuple(L),sign
def build(F):
    H=np.zeros((N,N))
    for i,D in enumerate(dets):
        for r,s in itertools.combinations(D,2):
            for p in range(10):
                for q in range(10):
                    if p==q: continue
                    val=g(so[p],so[q],so[r],so[s],F)-g(so[p],so[q],so[s],so[r],F)
                    if abs(val)<1e-12: continue
                    L,sign=apply(D,(s,r),(q,p))
                    if L is None: continue
                    H[idx[L],i]+=0.5*sign*val
    return H
v=np.zeros((5,5))
for i,m in enumerate(ms): v[i,i]={0:6,1:-4,2:1}[abs(m)]
v[0,4]=v[4,0]=5
V=np.zeros((N,N)); Sp=np.zeros((N,N))
for i,D in enumerate(dets):
    for r in D:
        for p in range(10):
            if so[p][1]!=so[r][1]: continue
            val=v[ms.index(so[p][0]),ms.index(so[r][0])]
            if val==0: continue
            L,sign=apply(D,(r,),(p,))
            if L is None: continue
            V[idx[L],i]+=sign*val
        if so[r][1]==0:
            L,sign=apply(D,(r,),(r+1,))
            if L is not None: Sp[idx[L],i]+=sign
H2=build({0:0,2:1.,4:0}); H4=build({0:0,2:0,4:1.})
HB=49*H2; HC=7*H2+(441/35)*H4
Sz=np.diag([sum(1 if so[o][1] else -1 for o in D)/2 for D in dets])
S2=Sp.T@Sp+Sz@Sz+Sz
c4=np.array([np.prod([np.exp(-1j*so[o][0]*np.pi/2) for o in D]) for D in dets])
def levels(Dq,B,Cc):
    H=Dq*V+B*HB+Cc*HC
    w,U=np.linalg.eigh(H)
    out=[];i=0
    while i<N:
        j=i
        while j<N and abs(w[j]-w[i])<1e-6*max(1,abs(w[i]))+1e-6: j+=1
        P=U[:,i:j]
        S=np.trace(P.T@S2@P)/(j-i); S=(-1+np.sqrt(1+4*S))/2
        ch=np.real(np.trace(P.conj().T@(c4[:,None]*P)))/(2*S+1)
        d=(j-i)/(2*S+1)
        lab={1:{1:'A1',-1:'A2'},2:{0:'E'},3:{1:'T1',-1:'T2'}}[round(d)][round(ch)]
        out.append((w[i],int(round(2*S+1)),lab));i=j
    return out
def names(Dq,B,Cc):
    o=levels(Dq,B,Cc);E0=o[0][1:]
    cnt={};res=[]
    for e,m,l in o:
        k=(m,l);cnt[k]=cnt.get(k,0)+1
        res.append((e-o[0][0],f"{m}{l}({cnt[k]})"))
    return res
print(names(800,800,3500)[:12])
obs={'4T2(1)':8480,'4A2(1)':16305,'4T1(2)':20360,'2T1(2)':21001}
def resid(x):
    d=dict((n,e) for e,n in names(*x))
    return [d[k]-v for k,v in obs.items()]
r=least_squares(resid,[800,800,3500])
print(r.x,resid(r.x))
for e,n in names(*r.x)[:14]: print(round(e),n)
