import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=784.;C=3699.
F2=49*B+7*C; F4=63*C/5
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    # <l m1|C^k|l m2> = (-1)^m1 sqrt(5*5)... use gaunt
    return float((-1)**m1*5*__import__('sympy').sqrt(__import__('sympy').Rational(1,2*k+1))*0+0)
from sympy import sqrt,Rational
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
F={0:0,2:F2,4:F4}
# orbitals spin: index (m,s)
so=[(m,s) for m in ms for s in (0,1)]
n=10
def V(a,b,cc,d): # <ab|1/r|cd>
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[a],so[b],so[cc],so[d]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0
    t=0
    for k in (2,4):
        t+=F[k]/ (1) *c(k,m1,m3)*c(k,m4,m2)*1.0 # c^k(l m1,l m3) c^k(l m4,l m2)
    return t
# note <m1|C|m3> convention fine for real result
Vt=np.zeros((n,)*4)
for a,b,cc,d in itertools.product(range(n),repeat=4): Vt[a,b,cc,d]=V(a,b,cc,d)
def run(Dq):
    h1=np.zeros((5,5),complex)
    idx={m:i for i,m in enumerate(ms)}
    eg=[np.zeros(5),np.zeros(5)]
    eg[0][idx[0]]=1; eg[1][idx[2]]=eg[1][idx[-2]]=2**-.5
    P=sum(np.outer(v,v) for v in eg)
    h1=6*Dq*P-4*Dq*(np.eye(5)-P)
    h=np.zeros((n,n))
    for a in range(n):
        for b in range(n):
            if so[a][1]==so[b][1]: h[a,b]=h1[idx[so[a][0]],idx[so[b][0]]].real
    dets=list(itertools.combinations(range(n),7))
    di={d:i for i,d in enumerate(dets)}
    H=np.zeros((len(dets),)*2)
    # build via second quantization
    def apply(ops,det):
        # ops list of (type, orb) applied right to left; return (sign,newdet) 
        occ=list(det);sign=1
        for t,o in reversed(ops):
            if t=='a':
                if o not in occ: return 0,None
                p=occ.index(o);sign*=(-1)**p;occ.pop(p)
            else:
                if o in occ: return 0,None
                p=sum(1 for x in occ if x<o);sign*=(-1)**p;occ.insert(p,o)
        return sign,tuple(occ)
    for det in dets:
        j=di[det]
        for a in range(n):
            for b in range(n):
                if h[a,b]!=0:
                    s,nd=apply([('c',a),('a',b)],det)
                    if s: H[di[nd],j]+=s*h[a,b]
        for a,b,cc,d in itertools.product(range(n),repeat=4):
            v=Vt[a,b,cc,d]
            if v==0: continue
            # 1/2 sum <ab|cd> a+_a a+_b a_d a_c
            s,nd=apply([('c',a),('c',b),('a',d),('a',cc)],det)
            if s: H[di[nd],j]+=0.5*s*v
    e=np.linalg.eigvalsh(H)
    e=e-e[0]
    # distinct levels
    L=[];
    for x in e:
        if not L or x-L[-1][0]>1e-3*B: L.append([x,1])
        else: L[-1][1]+=1
    return [(round(x/B,2),k) for x,k in L[:8]]
for D in (1.45,2.45,3.0): print(D,run(D*B))
