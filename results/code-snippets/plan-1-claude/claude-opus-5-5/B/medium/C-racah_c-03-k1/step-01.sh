
cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) * gaunt
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*np.sqrt(0)) if False else None
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
C={}
for k in (0,2,4):
    for a in ms:
        for b in ms: C[(k,a,b)]=c(k,a,b)
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,Cr):
    F0=0;F2=49*B+7*Cr;F4=441*Cr/35
    F={0:F0,2:F2,4:F4}
    def g(a,b,cc,d):# <ab|1/r|cd>
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[cc],so[d]
        if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
        return sum(F[k]*C[(k,ma,mc)]*C[(k,md,mb)] for k in (0,2,4))
    V=np.zeros((5,5))
    for i,m in enumerate(ms):
        V[i,i]={2:Dq,-2:Dq,1:-4*Dq,-1:-4*Dq,0:6*Dq}[m]
    V[0,4]=V[4,0]=5*Dq
    N=len(dets);H=np.zeros((N,N))
    for I,d in enumerate(dets):
        for J,e in enumerate(dets):
            # general via second quantization brute force
            pass
    # use operator approach
    def apply_1(p,q,det):
        det=list(det)
        if q not in det: return None
        s=(-1)**det.index(q); det.remove(q)
        if p in det: return None
        det.append(p); 
        # sort with sign
        arr=det; sign=s
        # insertion from end
        perm=sorted(range(len(arr)),key=lambda i:arr[i])
        # parity
        p_=list(perm);par=1
        vis=[False]*len(p_)
        for i in range(len(p_)):
            if not vis[i]:
                j=i;L=0
                while not vis[j]: vis[j]=True;j=p_[j];L+=1
                if L%2==0: par=-par
        # careful: appended p at end then sorted; sign from moving created op to front: creating at front gives sign; we placed at end -> extra (-1)^(n-1)
        sign*= par*(-1)**(len(arr)-1)
        return tuple(sorted(arr)),sign
    for I,d in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if so[p][1]!=so[q][1]: continue
                v=V[ms.index(so[p][0]),ms.index(so[q][0])]
                if v==0: continue
                r=apply_1(p,q,d)
                if r: H[idx[r[0]],I]+=v*r[1]
        for p in range(10):
         for q in range(10):
          for r_ in range(10):
           for s in range(10):
            val=g(p,q,s,r_)  # a+p a+q a_r a_s *1/2 <pq|rs>... 
            if val==0: continue
            x=apply_1(r_,r_,d) # dummy
            # a+p a+q a_r a_s
            t=apply_ann(d,s)
            pass
    return H
EOF
echo