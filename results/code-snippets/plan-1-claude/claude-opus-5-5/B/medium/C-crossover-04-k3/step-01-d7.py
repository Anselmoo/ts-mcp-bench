import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=922.,4156.
# F0 irrelevant; F2=49(B?) : B=(F2-5F4)/49 with F2,F4 normalized; use Fk: F2=49F2n, F4=441F4n
# A=F0-49F4n, B=F2n-5F4n, C=35F4n
F4n=C/35; F2n=B+5*F4n
Fk={0:0.,2:49*F2n,4:441*F4n}
l=2; ms=range(-2,3)
def ck(k,m1,m2): # c^k(l m1, l m2)
    return float((-1)**m1*np.sqrt((2*l+1)**2)/(2*l+1)*np.sqrt(4*np.pi/(2*k+1))*gaunt(l,k,l,-m1,m1-m2,m2)) if True else 0
# <m1 m2|1/r|m3 m4> = delta(m1+m2,m3+m4) sum_k ck(k,m1,m3)ck(k,m4,m2)Fk
U=np.zeros((5,5,5,5))
for a,b,c,d in itertools.product(range(5),repeat=4):
    m1,m2,m3,m4=[x-2 for x in (a,b,c,d)]
    if m1+m2!=m3+m4: continue
    U[a,b,c,d]=sum(ck(k,m1,m3)*ck(k,m4,m2)*Fk[k] for k in (0,2,4))
# crystal field octahedral in complex basis: Dq*(6,-4,6,-4 ... ) use standard: V = Dq*[[1,0,0,0,5],[0,-4,..]]
def hcf(Dq):
    h=np.zeros((5,5))
    h[0,0]=h[4,4]=Dq; h[1,1]=h[3,3]=-4*Dq; h[2,2]=6*Dq; h[0,4]=h[4,0]=5*Dq
    return h
so=[(m,s) for s in (0,1) for m in range(5)]
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
def apply2(det,p,q,r,s_):
    # a+_p a+_q a_s a_r
    st=list(det);sign=1
    for op,o in ((0,s_),(0,r),(1,q),(1,p)):
        if op==0:
            if o not in st: return None,0
            i=st.index(o);sign*=(-1)**i;st.pop(i)
        else:
            if o in st: return None,0
            i=sum(1 for x in st if x<o);sign*=(-1)**i;st.insert(i,o)
    return tuple(st),sign
N=len(dets)
H2=np.zeros((N,N));
for j,d in enumerate(dets):
    for p in range(10):
      for q in range(10):
        for r in range(10):
          for s_ in range(10):
            if so[p][1]!=so[r][1] or so[q][1]!=so[s_][1]: continue
            v=U[so[p][0],so[q][0],so[r][0],so[s_][0]]
            if abs(v)<1e-12: continue
            nd,sg=apply2(d,p,q,r,s_)
            if nd is None: continue
            H2[idx[nd],j]+=0.5*v*sg
def H1(Dq):
    h=hcf(Dq);M=np.zeros((N,N))
    for j,d in enumerate(dets):
        for p in range(10):
            for r in range(10):
                if so[p][1]!=so[r][1] or abs(h[so[p][0],so[r][0]])<1e-12: continue
                st=list(d)
                if r not in st: continue
                i=st.index(r);sg=(-1)**i;st.pop(i)
                if p in st: continue
                i=sum(1 for x in st if x<p);sg*=(-1)**i;st.insert(i,p)
                M[idx[tuple(st)],j]+=h[so[p][0],so[r][0]]*sg
    return M
H1u=H1(1.0)
Ms=np.array([sum(0.5 if so[o][1]==0 else -0.5 for o in d) for d in dets])
def gs(Dq):
    w,v=np.linalg.eigh(H2+Dq*H1u)
    # spin via S^2 estimate: degeneracy of ground
    return w[:20]
for Dq in (500,1500,2500):
    print(Dq,np.round(gs(Dq)-gs(Dq)[0],1))
def f(Dq):
    w=gs(Dq);e0=w[0]
    deg=sum(abs(w-e0)<1e-6)
    return deg
for Dq in np.arange(1000,3000,50): print(Dq,f(Dq))
