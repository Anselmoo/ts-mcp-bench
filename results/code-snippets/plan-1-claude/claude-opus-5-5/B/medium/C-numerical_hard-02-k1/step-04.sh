mkdir -p /tmp/w && cd /tmp/w && cat > d4.py <<'EOF'
import numpy as np, itertools
from math import factorial as f, sqrt
def w3j(j1,j2,j3,m1,m2,m3):
    if m1+m2+m3!=0: return 0.0
    t=lambda x:f(x)
    pre=(-1)**(j1-j2-m3)*sqrt(t(j1+j2-j3)*t(j1-j2+j3)*t(-j1+j2+j3)/t(j1+j2+j3+1))
    pre*=sqrt(t(j1+m1)*t(j1-m1)*t(j2+m2)*t(j2-m2)*t(j3+m3)*t(j3-m3))
    s=0
    for k in range(0,100):
        a=[k,j1+j2-j3-k,j1-m1-k,j2+m2-k,j3-j2+m1+k,j3-j1-m2+k]
        if min(a)<0: continue
        s+=(-1)**k/np.prod([t(x) for x in a])
    return pre*s
def ck(k,m,mp,l=2):
    return (-1)**m*(2*l+1)*w3j(l,k,l,0,0,0)*w3j(l,k,l,-m,m-mp,mp)
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
def g(a,b,c,d,F):  # <ab|cd>
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=[orbs[i] for i in (a,b,c,d)]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.0
    return sum(ck(k,m1,m3)*ck(k,m4,m2)*F[k] for k in (2,4))
def H(Dq,B,C,MS2=2):
    F={2:49*(B+C/7),4:441*C/35}
    V=np.zeros((5,5));idx={m:m+2 for m in range(-2,3)}
    for m,v in [(0,6),(1,-4),(-1,-4),(2,1),(-2,1)]: V[idx[m],idx[m]]=v*Dq
    V[idx[2],idx[-2]]=V[idx[-2],idx[2]]=5*Dq
    h1=np.zeros((10,10))
    for i,(mi,si) in enumerate(orbs):
        for j,(mj,sj) in enumerate(orbs):
            if si==sj: h1[i,j]=V[mi+2,mj+2]
    dets=[d for d in itertools.combinations(range(10),4) if sum(1 if orbs[i][1]==0 else -1 for i in d)==MS2]
    n=len(dets);Hm=np.zeros((n,n))
    # second quantization
    def apply(ops,det):
        # ops list of (dag,i) applied right to left
        occ=list(det);sign=1
        for dag,i in reversed(ops):
            if dag:
                if i in occ: return None,0
                p=sum(1 for x in occ if x<i);occ.append(i);occ.sort()
            else:
                if i not in occ: return None,0
                p=sum(1 for x in occ if x<i);occ.remove(i)
            sign*=(-1)**p
        return tuple(occ),sign
    di={d:k for k,d in enumerate(dets)}
    G={}
    for a in range(10):
      for b in range(10):
        for c in range(10):
          for d in range(10):
            v=g(a,b,c,d,F)
            if abs(v)>1e-12: G[(a,b,c,d)]=v
    for k,det in enumerate(dets):
        for i in range(10):
            for j in range(10):
                if abs(h1[i,j])>1e-12:
                    nd,s=apply([(1,i),(0,j)],det)
                    if nd in di: Hm[di[nd],k]+=s*h1[i,j]
        for (a,b,c,d),v in G.items():
            nd,s=apply([(1,a),(1,b),(0,d),(0,c)],det)
            if nd in di: Hm[di[nd],k]+=0.5*s*v
    return Hm
def levels(Dq,B,C):
    e1=np.linalg.eigvalsh(H(Dq,B,C,2)); e2=np.linalg.eigvalsh(H(Dq,B,C,4))
    # triplets: in MS=1 but not MS=2 ; remove quintet energies
    e1=list(np.round(e1,4)); 
    for x in np.round(e2,4):
        # remove one copy
        i=np.argmin(np.abs(np.array(e1)-x)); e1.pop(i)
    return np.array(sorted(e1)), np.array(sorted(e2))
EOF
cat > run.py <<'EOF'
from d4 import *
import numpy as np
def trip_terms(Dq,B):
    t,q=levels(Dq,B,4.3*B)
    # group degeneracies
    g=[];
    for x in t:
        if g and abs(x-g[-1][0])<1e-2: g[-1][1]+=1
        else: g.append([x,1])
    return g,q
g,q=trip_terms(2500,600)
print([(round(x-g[0][0]),n) for x,n in g][:10]); print(round(q[0]-g[0][0]))
EOF
python3 run.py