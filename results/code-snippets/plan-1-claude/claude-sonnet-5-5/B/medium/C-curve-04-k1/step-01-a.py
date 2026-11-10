import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from math import sqrt
B=800.;C=3473.
F4=63*C/5;F2=(441*B+5*F4)/9
F={0:0,2:F2,4:F4}
l=2
def ck(k,m1,m2):
    # <l m1|C^k_q|l m2>, q=m1-m2
    q=m1-m2
    return float((-1)**m1*(2*l+1)*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m1,q,m2))
ms=[-2,-1,0,1,2]
# <ab|1/r|cd> = sum_k F^k c^k(a,c) c^k(b,d) with a,c electron1; F0 term needed const only (5 electrons fixed) -> drop F0 but keep consistent: include F0=0
def V(a,b,c,d):
    if a+b!=c+d: return 0
    s=0
    for k in (2,4):
        s+=F[k]*ck(k,a,c)*ck(k,b,d)*(-1)**0  # c^k(l m|l m') real sign convention
        pass
    return s
# sign: <a|C^k_q|c><b|C^k_-q|d> = (-1)^q c^k(a,c)c^k(d,b)
def Vv(a,b,c,d):
    if a+b!=c+d: return 0
    q=a-c;s=0
    for k in (2,4):
        s+=F[k]*(-1)**q*ck(k,a,c)*ck(k,d,b)
    return s
so=[(m,s) for m in ms for s in (0,1)]
def run(Dq):
    h=np.zeros((5,5))
    for m,v in zip(ms,[Dq]*5): pass
    d={0:6,1:-4,-1:-4,2:1,-2:1}
    for m in ms:h[m+2,m+2]=d[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    dets=list(itertools.combinations(range(10),5))
    idx={x:i for i,x in enumerate(dets)}
    n=len(dets);H=np.zeros((n,n));S2=np.zeros((n,n))
    # build via second quantization
    def apply(ops,det):
        # ops list of (type,orb) applied right to left; returns (sign,det) or None
        det=list(det);sg=1
        for t,o in reversed(ops):
            if t=='a':
                if o not in det:return None
                p=det.index(o);sg*=(-1)**p;det.pop(p)
            else:
                if o in det:return None
                p=sum(1 for x in det if x<o);sg*=(-1)**p;det.insert(p,o)
        return sg,tuple(det)
    spo=[(m,s) for m in ms for s in (0,1)]
    # spin orbital index i = (m,s)
    for j,det in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if spo[p][1]!=spo[q][1]:continue
                x=h[spo[p][0]+2,spo[q][0]+2]
                if x==0:continue
                r=apply([('c',p),('a',q)],det)
                if r:H[idx[r[1]],j]+=x*r[0]
        for p in range(10):
         for q in range(10):
          for r_ in range(10):
           for s_ in range(10):
            a,sa=spo[p];b,sb=spo[q];c,sc=spo[r_];dd,sd=spo[s_]
            if sa!=sc or sb!=sd:continue
            x=Vv(a,b,c,dd)
            if x==0:continue
            r=apply([('c',p),('c',q),('a',s_),('a',r_)],det)
            if r:H[idx[r[1]],j]+=0.5*x*r[0]
    # S2 via Sz and S-S+
    def Sp(det):
        out={}
        for i in det:
            m,s=spo[i]
            if s==0:
                r=apply([('c',i+1),('a',i)],det)
                if r:out[r[1]]=out.get(r[1],0)+r[0]
        return out
    Sm=np.zeros((n,n))
    for j,det in enumerate(dets):
        for k,v in Sp(det).items():Sm[idx[k],j]+=v
    Sz=np.diag([sum(.5 if spo[i][1]==0 else -.5 for i in det) for det in dets])
    S2=Sm.T@Sm+Sz@Sz+Sz  # S-S+ = S2 - Sz^2 - Sz
    S2=Sm.T@Sm+Sz@Sz+Sz
    w,v=np.linalg.eigh(H+0.001*S2)
    s2=np.einsum('ij,ik,kj->j',v,v,S2@v) if False else np.array([v[:,i]@S2@v[:,i] for i in range(n)])
    w=np.array([v[:,i]@H@v[:,i] for i in range(n)])
    return w,s2
for x in (1.45,2.55,3.25):
    w,s2=run(x*B)
    o=np.argsort(w);w=w[o];s2=s2[o]
    lv=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3*B:j+=1
        lv.append(((w[i]-w[0])/B,j-i,round(s2[i],2)));i=j
    print(x,lv[:7])
