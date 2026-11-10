
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
l=2
def ck(k,m1,m2):  # c^k(l m1, l m2)
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*(2*l+1)*gaunt(l,k,l,-m1,m1-m2,m2))
C={}
for k in (0,2,4):
  for a in range(-2,3):
    for b in range(-2,3):
      C[(k,a,b)]=ck(k,a,b)
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),5) if sum(orbs[i][1] for i in d)==3]  # Ms= (3*... ) choose Ms=1/2? 
# Ms = (#up - #down)/2 ; s=1 is up: 3 up 2 down -> Ms=1/2 contains sextet and quartets
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,Cc):
    F2=B+5*Cc/35; F4=Cc/35
    Fk={0:0.0,2:49*F2,4:441*F4}
    n=len(dets);H=np.zeros((n,n))
    V=np.zeros((5,5))
    for m in range(-2,3):
        V[m+2,m+2]={0:6,1:-4,2:1}[abs(m)]*Dq
    V[4,0]=V[0,4]=5*Dq
    def g(i,j,k,l_):  # <ij|1/r|kl>
        (mi,si),(mj,sj),(mk,sk),(ml,sl)=orbs[i],orbs[j],orbs[k],orbs[l_]
        if si!=sk or sj!=sl or mi+mj!=mk+ml: return 0.0
        return sum(C[(k_,mi,mk)]*C[(k_,ml,mj)]*Fk[k_] for k_ in (2,4))
    for d in dets:
        I=idx[d]
        # one-body
        for p in d:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[orbs[p][0]+2,orbs[q][0]+2]
                if v==0: continue
                if q!=p and q in d: continue
                nd=list(d); pos=nd.index(p); nd[pos]=q
                sign=(-1)**sum(1 for x in nd if x<q and x!=q) if False else None
                # compute sign via sorting
                perm=np.argsort(nd); s=np.linalg.det(np.eye(5)[perm]) 
                H[idx[tuple(sorted(nd))],I]+=v*s
        # two-body: sum_{p<q in d} sum_{r<s} <rs||pq> a_r+ a_s+ a_q a_p
        for p,q in itertools.combinations(d,2):
            rest=[x for x in d if x not in (p,q)]
            for r in range(10):
                for s_ in range(10):
                    if r>=s_: continue
                    if (r in rest) or (s_ in rest): continue
                    v=g(r,s_,p,q)-g(r,s_,q,p)
                    if abs(v)<1e-12: continue
                    # sign: remove p,q from d, add r,s
                    # annihilate: position signs
                    lst=list(d); sg=1
                    i_q=lst.index(q); sg*=(-1)**i_q; lst.pop(i_q)
                    i_p=lst.index(p); sg*=(-1)**i_p; lst.pop(i_p)
                    # create s then r
                    for c in (s_,r):
                        pos=sum(1 for x in lst if x<c); sg*=(-1)**pos; lst.insert(pos,c)
                    H[idx[tuple(lst)],I]+=v*sg
    return H
def S2(): pass
def levels(Dq,B,Cc):
    H=build(Dq,B,Cc); w=np.linalg.eigvalsh(H); return w
w=levels(0,1,0); 
print(np.round(np.unique(np.round(w,4)),3)[:10])
EOF
python3 /tmp/d5.py
