
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
l=2;ms=range(-2,3)
def ck(k,m1,m2): # <l m1|C^k|l m2>
    return float((-1)**m1*np.sqrt(5*5)*gaunt(2,k,2,-m1,m1-m2,m2)) if False else float((-1)**m1*5*gaunt(2,2 if False else k,2,0,0,0)*0) 
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,m1-m2,m2)*wigner_3j(2,k,2,0,0,0))
# orbitals idx: (m,s)
orbs=[(m,s) for m in ms for s in (0,1)]
def Vint(F,a,b,c_,d): # <ab|1/r|cd> orbitals m
    ma,mb,mc,md=a,b,c_,d
    if ma+mb!=mc+md:return 0
    t=0
    for k,Fk in ((0,F[0]),(2,F[1]),(4,F[2])):
        # <ma mb|g|mc md> = sum_k ck(ma,mc) ck(md,mb) F^k
        t+=Fk*(-1)**(ma-mc)*float(0)+0
    return t
def ckk(k,m1,m2): return c(k,m1,m2)
def build(Dq,B,C):
    F=[0,49*B+7*C,63*C/5]
    # one-body in real basis: dz2,dx2-y2,dxy,dxz,dyz ; complex combos
    s=1/np.sqrt(2)
    # real orbitals in terms of m: z2=m0; x2-y2=(m2+m-2)/√2; xy=(m-2 - m2)*i/√2 ; xz, yz
    U=np.zeros((5,5),complex) # columns real orbitals, rows m=-2..2
    idx={m:m+2 for m in ms}
    U[idx[0],0]=1
    U[idx[2],1]=s;U[idx[-2],1]=s
    U[idx[2],2]=-1j*s;U[idx[-2],2]=1j*s
    U[idx[1],3]=-s;U[idx[-1],3]=s
    U[idx[1],4]=1j*s;U[idx[-1],4]=1j*s
    e=np.diag([6*Dq,6*Dq,-4*Dq,-4*Dq,-4*Dq])
    h=U@e@U.conj().T
    # two-body g[a,b,c,d]=<ab|cd> (spatial)
    g=np.zeros((5,5,5,5))
    for a in ms:
     for b in ms:
      for cc in ms:
       for d in ms:
        if a+b!=cc+d: continue
        g[a+2,b+2,cc+2,d+2]=sum(F[k//2]*c(k,a,cc)*c(k,d,b) for k in (2,4)) 
    return h,g
def run(Dq,B,C):
    h,g=build(Dq,B,C)
    N=10
    dets=list(itertools.combinations(range(N),6))
    di={d:i for i,d in enumerate(dets)}
    H=np.zeros((len(dets),)*2,complex); S2=np.zeros_like(H)
    mo=lambda o:(o//2)-2; so=lambda o:o%2
    def apply_ann(d,o):
        if o not in d:return None
        p=d.index(o);return tuple(x for x in d if x!=o),(-1)**p
    def apply_cr(d,o):
        if o in d:return None
        p=sum(1 for x in d if x<o);return tuple(sorted(d+(o,))),(-1)**p
    # operators on det
    for d in dets:
        j=di[d]
        for p in range(N):
          for q in range(N):
            if so(p)!=so(q):continue
            v=h[mo(p)+2,mo(q)+2]
            if abs(v)<1e-12:continue
            r=apply_ann(d,q)
            if r is None:continue
            d1,s1=r;r=apply_cr(d1,p)
            if r is None:continue
            H[di[r[0]],j]+=v*s1*r[1]
        for p in range(N):
         for q in range(N):
          for r_ in range(N):
           for s_ in range(N):
             # 1/2 <pq|rs> a+p a+q a_s a_r  (spin p=r, q=s)
             if so(p)!=so(r_) or so(q)!=so(s_):continue
             v=g[mo(p)+2,mo(q)+2,mo(r_)+2,mo(s_)+2]
             if v==0:continue
             x=apply_ann(d,r_)
             if not x:continue
             d1,s1=x;x=apply_ann(d1,s_)
             if not x:continue
             d2,s2=x;x=apply_cr(d2,q)
             if not x:continue
             d3,s3=x;x=apply_cr(d3,p)
             if not x:continue
             H[di[x[0]],j]+=0.5*v*s1*s2*s3*x[1]
    return H,dets,di
E
echo