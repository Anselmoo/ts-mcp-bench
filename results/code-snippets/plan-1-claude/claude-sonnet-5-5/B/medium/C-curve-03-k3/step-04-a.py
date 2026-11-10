import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from collections import Counter
B=784.;C=3699.
F4=C/35;F2=B+5*F4;F={2:49*F2,4:441*F4}
def c(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
V=np.zeros((5,5,5,5))
for a,b_,cc,d in itertools.product(range(5),repeat=4):
    m1,m2,m3,m4=[x-2 for x in (a,b_,cc,d)]
    if m1+m2!=m3+m4: continue
    V[a,b_,cc,d]=sum(F[k]*c(k,m1,m3)*c(k,m4,m2) for k in (2,4))
N=10
dets=list(itertools.combinations(range(N),7)); idx={d:i for i,d in enumerate(dets)}
def apply_ops(ops,state):
    sg=1
    for op,dag in reversed(ops):
        if dag:
            if op in state: return None
            pos=sum(1 for x in state if x<op); state=tuple(sorted(state+(op,)))
        else:
            if op not in state: return None
            pos=state.index(op); state=tuple(x for x in state if x!=op)
        sg*=(-1)**pos
    return state,sg
def run(Dq):
    s=1/np.sqrt(2)
    def vec(d):
        v=np.zeros(5,complex)
        for m,x in d.items(): v[m+2]=x
        return v
    z2=vec({0:1}); x2=vec({2:s,-2:s}); xy=vec({2:-1j*s,-2:1j*s})
    xz=vec({1:s,-1:-s}); yz=vec({1:1j*s,-1:1j*s})
    h=sum(6*Dq*np.outer(v,v.conj()) for v in (z2,x2))+sum(-4*Dq*np.outer(v,v.conj()) for v in (xy,xz,yz))
    H=np.zeros((120,120),complex); S2=np.zeros((120,120),complex)
    for st in dets:
        j=idx[st]
        for o1 in range(5):
          for o2 in range(5):
            if abs(h[o1,o2])>1e-12:
              for s_ in range(2):
                r=apply_ops([(2*o1+s_,1),(2*o2+s_,0)],st)
                if r: H[idx[r[0]],j]+=h[o1,o2]*r[1]
        for a,b_,cc,d in itertools.product(range(5),repeat=4):
            if V[a,b_,cc,d]==0: continue
            for s1 in range(2):
                for s2 in range(2):
                    r=apply_ops([(2*a+s1,1),(2*b_+s2,1),(2*d+s2,0),(2*cc+s1,0)],st)
                    if r: H[idx[r[0]],j]+=0.5*V[a,b_,cc,d]*r[1]
        sz=sum(0.5 if x%2==0 else -0.5 for x in st)
        S2[j,j]+=sz*sz+sz
        for o in range(5):
            for o2 in range(5):
                r=apply_ops([(2*o+1,1),(2*o,0),(2*o2,1),(2*o2+1,0)],st)
                if r: S2[idx[r[0]],j]+=r[1]
    return H,S2
for x in [1.45,2.45,3.0]:
    H,S2=run(x*B)
    M=H+1e-3*S2
    w,v=np.linalg.eigh((M+M.conj().T)/2)
    w0=w.min(); out=[]
    for i in range(120):
        s2=(v[:,i].conj()@S2@v[:,i]).real
        S=(-1+np.sqrt(1+4*s2))/2
        out.append((round((w[i]-w0)/B,2),round(S*2)/2))
    cnt=Counter(out)
    print(x,[(k,v/(2*k[1]+1)) for k,v in sorted(cnt.items())][:9])
