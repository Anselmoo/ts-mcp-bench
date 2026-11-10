
cat > <SANDBOX_TMP>/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=784.;C=3699.
F={2:49*B+7*C,4:63*C/5}
ms=[-2,-1,0,1,2]
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
so=[(m,s) for m in ms for s in (0,1)]
n=10
Vt=np.zeros((n,)*4)
for a,b,cc,d in itertools.product(range(n),repeat=4):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[a],so[b],so[cc],so[d]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: continue
    Vt[a,b,cc,d]=sum(F[k]*c(k,m1,m3)*c(k,m4,m2) for k in (2,4))
dets=list(itertools.combinations(range(n),7))
di={d:i for i,d in enumerate(dets)}
def apply(ops,det):
    occ=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in occ: return 0,None
            p=occ.index(o);sign*=(-1)**p;occ.pop(p)
        else:
            if o in occ: return 0,None
            p=sum(1 for x in occ if x<o);sign*=(-1)**p;occ.insert(p,o)
    return sign,tuple(occ)
H2=np.zeros((120,120));H1=[np.zeros((120,120))]
idx={m:i for i,m in enumerate(ms)}
eg=[np.zeros(5),np.zeros(5)]
eg[0][idx[0]]=1; eg[1][idx[2]]=eg[1][idx[-2]]=2**-.5
P=sum(np.outer(v,v) for v in eg)
h1=10*P-4*np.eye(5)  # per Dq
h=np.zeros((n,n))
for a in range(n):
    for b in range(n):
        if so[a][1]==so[b][1]: h[a,b]=h1[idx[so[a][0]],idx[so[b][0]]]
Hc=np.zeros((120,120))
for det in dets:
    j=di[det]
    for a in range(n):
        for b in range(n):
            if h[a,b]!=0:
                s,nd=apply([('c',a),('a',b)],det)
                if s: Hc[di[nd],j]+=s*h[a,b]
    for a,b,cc,d in itertools.product(range(n),repeat=4):
        v=Vt[a,b,cc,d]
        if v==0: continue
        s,nd=apply([('c',a),('c',b),('a',d),('a',cc)],det)
        if s: H2[di[nd],j]+=0.5*s*v
for D in (1.45,2.45,3.0):
    e=np.linalg.eigvalsh(H2+D*B*Hc); e-=e[0]
    L=[]
    for x in e:
        if not L or x-L[-1][0]>1e-3*B: L.append([x,1])
        else: L[-1][1]+=1
    print(D,[(round(x/B,2),k) for x,k in L[:8]])
E
python3 <SANDBOX_TMP>/a.py