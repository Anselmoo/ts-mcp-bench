
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
l=2;ms=range(-2,3)
def ck(k,m1,m2): # <l m1|C^k|l m2> with q=m1-m2
    return float((-1)**m1*(2*l+1)*gaunt(l,k,l,-m1,m1-m2,m2)) if True else 0
# <m1|C^k_q|m2> = (-1)^m1 (2l+1) 3j(l k l;-m1 q m2)(l k l;000)
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,m1-m2,m2)*wigner_3j(2,k,2,0,0,0))
C={(k,a,b):c(k,a,b) for k in(0,2,4) for a in ms for b in ms}
# complex-basis V(ab,cd)=sum_k F^k c(a,c)c(b,d) ... <ab|1/r12|cd> = sum_k Fk ck(a,c) ck(b,d) with m conservation (a-c = d-b)
def Vc(k):
    V=np.zeros((5,5,5,5))
    for a in ms:
     for b in ms:
      for cc in ms:
       for d in ms:
        if a+b==cc+d:
         V[a+2,b+2,cc+2,d+2]=C[(k,a,cc)]*C[(k,d,b)]*(-1)**(a-cc)
    return V
# check sign: <ab|cd> = sum_k F^k c^k(l a;l c) c^k(l b; l d)... with c^k(a,c)=(-1)^a... use standard: c^k(m,m')=sqrt-stuff; direct: C(a,c)*C(b,d)
def Vc(k):
    V=np.zeros((5,5,5,5))
    for a in ms:
     for b in ms:
      for cc in ms:
       for d in ms:
        if a+b==cc+d:
         V[a+2,b+2,cc+2,d+2]=C[(k,a,cc)]*C[(k,b,d)]*1.0
    return V
# <a b|cd> = sum_k F^k <a|Ck|c><b|Ck(-)|d>; <b|C^k_{-q}|d> = (-1)^q <d|C^k_q|b>* -> use conj sym: c(k,b,d) with q'=b-d=-(a-c): ok as computed.
# Note sign (-1)^q needed: <a|C_q|c><b|C_-q|d> * (-1)^q
def Vc(k):
    V=np.zeros((5,5,5,5))
    for a in ms:
     for b in ms:
      for cc in ms:
       for d in ms:
        if a+b==cc+d:
         V[a+2,b+2,cc+2,d+2]=C[(k,a,cc)]*C[(k,b,d)]*(-1)**(a-cc)
    return V
V2,V4=Vc(2),Vc(4)
# real orbitals order: z2,xz,yz,x2-y2,xy
s=1/np.sqrt(2)
U=np.zeros((5,5),complex) # real_i = sum_m U[i,m] |m>
def idx(m):return m+2
U[0,idx(0)]=1
U[1,idx(1)]=s;U[1,idx(-1)]=-s   # xz
U[2,idx(1)]=1j*s;U[2,idx(-1)]=1j*s #yz
U[3,idx(2)]=s;U[3,idx(-2)]=s
U[4,idx(2)]=-1j*s;U[4,idx(-2)]=1j*s
def tr(V):
    # <ab|cd> real = sum conj(U ia)conj(U jb) U kc U ld V
    return np.einsum('ia,jb,kc,ld,abcd->ijkl',U.conj(),U.conj(),U,U,V).real
R2,R4=tr(V2),tr(V4)
# orbitals spin: so=(orb,spin)
so=[(o,s_) for o in range(5) for s_ in (0,1)]
dets=list(itertools.combinations(range(10),7))
di={d:i for i,d in enumerate(dets)}
def build(Dq,B,Cc):
    F2=49*B+7*Cc; F4=63*Cc/5*0+ (441*Cc/35)  # C=(35F4)/441 in this F4 normalization? set below
    # Condon-Shortley: B=F2-5F4, C=35F4 with F2,F4 = F^k/49,/441
    f4=Cc/35; f2=B+5*f4
    F2=f2*49;F4=f4*441
    # two-electron <ab|cd>
    G=F2*R2+F4*R4
    h=np.zeros(10)
    for i,(o,sp) in enumerate(so): h[i]= (6*Dq if o in(0,3) else -4*Dq)
    N=len(dets);H=np.zeros((N,N))
    def apply(ops,det): # ops list of (i,create?) apply right to left
        det=list(det);sign=1
        for i,cr in ops:
            if cr:
                if i in det:return None,0
                pos=sum(1 for x in det if x<i);det.insert(pos,i);sign*=(-1)**pos
            else:
                if i not in det:return None,0
                pos=det.index(i);det.pop(pos);sign*=(-1)**pos
        return tuple(det),sign
    for n,d in enumerate(dets):
        for i in d:H[n,n]+=h[i]
        # 1/2 sum <pq|rs> a+p a+q a_s a_r
        for r in d:
          for t in d:
            if r==t:continue
            for p in range(10):
              for q in range(10):
                if so[p][1]!=so[r][1] or so[q][1]!=so[t][1]:continue
                val=G[so[p][0],so[q][0],so[r][0],so[t][0]]
                if val==0:continue
                nd,sg=apply([(r,0),(t,0),(q,1),(p,1)],d)
                if nd is None:continue
                H[di[nd],n]+=0.5*val*sg
    return H
def levels(Dq,B,Cc):
    w=np.linalg.eigvalsh(build(Dq,B,Cc));return w
import sys
w=levels(800,900,3500);w=np.unique(np.round(w-w[0],3));print(w[:12])
np.save('/tmp/x',0)
def model(p):
    Dq,B,Cc=p
    w=np.linalg.eigvalsh(build(Dq,B,Cc));w-=w[0]
    return w
# identify by spin multiplicity is hard; use matching by nearest degenerate levels
def lev(p):
    w=model(p);u=[];
    for x in w:
        if not u or abs(x-u[-1][0])>1:u.append([x,1])
        else:u[-1][1]+=1
    return u
for x in lev((800,900,3500))[:15]:print(x)
E
python3 /tmp/a.py
