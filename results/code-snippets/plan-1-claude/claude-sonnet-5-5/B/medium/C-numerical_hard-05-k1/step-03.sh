
python3 - <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ml=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
C={(k,a,b):ck(k,a,b) for k in (2,4) for a in ml for b in ml if abs(a-b)<=k}
def cc(k,a,b): return C.get((k,a,b),0.0)
def Vint(F,a,b,c,d):
    if a+b!=c+d: return 0
    return sum(F[k]*cc(k,a,c)*cc(k,d,b) for k in (2,4))
orbs=[(m,s) for m in ml for s in (0,1)]
dets=[c for c in itertools.combinations(range(10),6) if sum(1 for o in c if o%2==0)==3]
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
s2=1/np.sqrt(2)
def ann(d,o):
    if o not in d:return None
    return tuple(x for x in d if x!=o),(-1)**d.index(o)
def cre(d,o):
    if o in d:return None
    l=sorted(d+(o,));return tuple(l),(-1)**l.index(o)
# S2 matrix
S=np.zeros((N,N))
for I,d in enumerate(dets):
    S[I,I]+=0  # sz=0
    for p in ml:
      for q in ml:
        pu,pd,qu,qd=[2*(x+2)+y for x,y in((p,0),(p,1),(q,0),(q,1))]
        cur=d;sg=1
        r=ann(cur,qd)
        if not r: continue
        cur,s=r;sg*=s
        r=cre(cur,qu)
        if not r: continue
        cur,s=r;sg*=s
        r=ann(cur,pu)
        if not r: continue
        cur,s=r;sg*=s
        r=cre(cur,pd)
        if not r: continue
        cur,s=r;sg*=s
        S[idx[cur],I]+=sg
S=(S+S.T)/2
# precompute g
g=np.zeros((10,10,10,10,2))
def gfun(F):
    G={}
    for i,(a,s1) in enumerate(orbs):
     for j,(b,sb) in enumerate(orbs):
      for k,(c,s3) in enumerate(orbs):
       for l,(d,s4) in enumerate(orbs):
        if s1==s3 and sb==s4:
            v=Vint(F,a,b,c,d)
            if v!=0:G[(i,j,k,l)]=v
    return G
def build(Dq,B,Cc):
    F={2:49*B+7*Cc,4:63*Cc/5}
    v0=np.zeros(5);v0[2]=1
    v1=np.zeros(5);v1[4]=s2;v1[0]=s2
    P=6*Dq*(np.outer(v0,v0)+np.outer(v1,v1))
    t=[np.zeros(5,complex) for _ in range(3)]
    t[0][4]=s2/1j;t[0][0]=-s2/1j
    t[1][3]=1;t[2][1]=1
    P=P-4*Dq*sum(np.outer(x,x.conj()) for x in t)
    H=np.zeros((N,N),complex)
    Gd=gfun(F)
    for I,d in enumerate(dets):
        for i,(m,s) in enumerate(orbs):
          for j,(n,r_) in enumerate(orbs):
            if s!=r_ or abs(P[m+2,n+2])<1e-12:continue
            r=ann(d,j)
            if not r:continue
            d1,s_=r;r=cre(d1,i)
            if not r:continue
            H[idx[r[0]],I]+=P[m+2,n+2]*s_*r[1]
        for (i,j,k,l),v in Gd.items():
            r=ann(d,k)
            if not r:continue
            d1,a=r;r=ann(d1,l)
            if not r:continue
            d2,b=r;r=cre(d2,j)
            if not r:continue
            d3,c=r;r=cre(d3,i)
            if not r:continue
            H[idx[r[0]],I]+=0.5*v*a*b*c*r[1]
    return H
def levels(Dq,B):
    H=build(Dq,B,4.5*B)
    H=(H+H.conj().T)/2
    w,v=np.linalg.eigh(H+0.01*S)
    s=np.real(np.einsum('ij,ik,kj->j',v.conj(),S,v))
    e=np.real(np.einsum('ij,ik,kj->j',v.conj(),H,v))
    sing=np.sort(e[s<0.3]); sing=sing-sing[0]
    u=[]
    for x in sing:
        if not u or abs(x-u[-1][0])>5:u.append([x,1])
        else:u[-1][1]+=1
    return u
print(levels(2000,500)[:8])
obs=np.array([13960,22740,29700])
def res(p):
    t=[x for x,n in levels(*p) if n==3][:3]
    return np.array(t)-obs
for gg in [(2000,400),(1500,500)]:
    r=least_squares(res,gg,diff_step=1e-3);print(r.x,r.fun,levels(*r.x)[:8])
E
