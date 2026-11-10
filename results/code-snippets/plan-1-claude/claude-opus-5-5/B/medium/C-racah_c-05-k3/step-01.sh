
cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2; ms=range(-2,3)
# spin orbitals (m,s)
so=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    # c^k(l m1, l m2) = <l m1|C^k_{m1-m2}|l m2>
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*np.sqrt(5*5)*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2)) if True else 0
import functools
@functools.lru_cache(None)
def c(k,m1,m2): return ck(k,m1,m2)
def Rint(m1,m2,m3,m4,F):
    # <m1 m2|1/r|m3 m4>, m1+m2=m3+m4
    if m1+m2!=m3+m4: return 0.0
    return sum(F[k]*c(k,m1,m3)*c(k,m4,m2) for k in (0,2,4))
def build(Dq,B,C):
    F={0:0,2:49*(B+C/7*0)+0,4:0}
    F2=49*B+7*C; F4=441*C/35
    F={0:0,2:F2,4:F4}
    # cubic one-electron in complex basis: Dq*(6 for m=0, -4 for ±1, 1 for ±2 plus 5 for +-2 mixing)
    h=np.zeros((5,5))
    idx={m:i for i,m in enumerate(ms)}
    h[idx[0],idx[0]]=6*Dq; h[idx[1],idx[1]]=h[idx[-1],idx[-1]]=-4*Dq
    h[idx[2],idx[2]]=h[idx[-2],idx[-2]]=Dq; h[idx[2],idx[-2]]=h[idx[-2],idx[2]]=5*Dq
    dets=list(itertools.combinations(range(10),3))
    N=len(dets); H=np.zeros((N,N))
    def g(a,b,cc,d):
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[cc],so[d]
        if sa!=sc or sb!=sd: return 0.0
        return Rint(ma,mb,mc,md,F)
    for I,D1 in enumerate(dets):
        for J,D2 in enumerate(dets):
            s1=set(D1); s2=set(D2)
            diff=len(s1-s2)
            if diff>2: continue
            # generic via second quantization
            val=0.0
            # one body
            for p in range(10):
                for q in range(10):
                    if so[p][1]!=so[q][1]: continue
                    hv=h[idx[so[p][0]],idx[so[q][0]]]
                    if hv==0: continue
                    sg,st=apply([('a',q),('c',p)],D2)
                    if st==D1: val+=sg*hv
            H[I,J]=val
    # two body
    for J,D2 in enumerate(dets):
        for p,q in itertools.permutations(range(10),2):
            for r,s in itertools.permutations(range(10),2):
                if r not in D2 or s not in D2: continue
                gv=g(p,q,r,s)
                if gv==0: continue
                sg,st=apply([('a',r),('a',s),('c',q),('c',p)],D2)
                if st is None: continue
                H[dets.index(st),J]+=0.5*sg*gv
    return H,dets
def apply(ops,D):
    st=list(D); sign=1
    for t,o in ops:
        if t=='a':
            if o not in st: return 0,None
            i=st.index(o); sign*=(-1)**i; st.pop(i)
        else:
            if o in st: return 0,None
            st.insert(0,o); 
            # sort
            k=0
            while k<len(st)-1 and st[k]>st[k+1]:
                st[k],st[k+1]=st[k+1],st[k]; sign*=-1; k+=1
    return sign,tuple(st)
def levels(Dq,B,C):
    H,d=build(Dq,B,C); w=np.linalg.eigvalsh(H); w=w-w[0]
    return np.round(w,1)
w=levels(1750,618,618*4)
print(sorted(set(w))[:8])
EOF
python3 /tmp/d3.py
