import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=922.,4156.
F4n=C/35; F2n=B+5*F4n
Fk={0:0.,2:49*F2n,4:441*F4n}
l=2
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(l,k,l,-m1,m1-m2,m2))
U=np.zeros((5,5,5,5))
for a,b,c,d in itertools.product(range(5),repeat=4):
    m1,m2,m3,m4=[x-2 for x in (a,b,c,d)]
    if m1+m2!=m3+m4: continue
    U[a,b,c,d]=sum(ck(k,m1,m3)*ck(k,m4,m2)*Fk[k] for k in (0,2,4))
h=np.zeros((5,5))
h[0,0]=h[4,4]=1; h[1,1]=h[3,3]=-4; h[2,2]=6; h[0,4]=h[4,0]=5
so=[(m,s) for s in (0,1) for m in range(5)]
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def ops(det,seq):
    st=list(det);sign=1
    for op,o in seq:
        if op==0:
            if o not in st: return None,0
            i=st.index(o);sign*=(-1)**i;st.pop(i)
        else:
            if o in st: return None,0
            i=sum(1 for x in st if x<o);sign*=(-1)**i;st.insert(i,o)
    return tuple(st),sign
H2=np.zeros((N,N));H1=np.zeros((N,N));S2=np.zeros((N,N))
for j,d in enumerate(dets):
  for p in range(10):
    for r in range(10):
      if so[p][1]==so[r][1] and abs(h[so[p][0],so[r][0]])>1e-12:
        nd,sg=ops(d,[(0,r),(1,p)])
        if nd: H1[idx[nd],j]+=h[so[p][0],so[r][0]]*sg
      for q in range(10):
        for s_ in range(10):
          if so[p][1]!=so[r][1] or so[q][1]!=so[s_][1]: continue
          v=U[so[p][0],so[q][0],so[r][0],so[s_][0]]
          if abs(v)<1e-12: continue
          nd,sg=ops(d,[(0,r),(0,s_),(1,q),(1,p)])
          if nd: H2[idx[nd],j]+=0.5*v*sg
for j,d in enumerate(dets):
  ms=sum(0.5 if so[o][1]==0 else -0.5 for o in d)
  S2[j,j]+=ms*ms-ms
  for m in range(5):
    for m2 in range(5):
      nd,sg=ops(d,[(0,m2),(1,m2+5),(0,m+5),(1,m)])
      if nd: S2[idx[nd],j]+=sg
w=np.linalg.eigvalsh(H2); print(np.round((w-w[0])/B,2)[::4][:20])
def info(Dq):
    w,v=np.linalg.eigh(H2+Dq*H1)
    s=np.einsum('ij,ik,kj->j',v[:,:40],S2,v[:,:40])
    return w,s
for Dq in (1000,2500):
    w,s=info(Dq); print(Dq,np.round(w[:40:2]-w[0],0),np.round(s[:40:2],2))
def g(Dq):
    w,s=info(Dq)
    q=min(w[i] for i in range(40) if abs(s[i]-3.75)<0.1)
    d=min(w[i] for i in range(40) if abs(s[i]-0.75)<0.1)
    return q-d
r=brentq(g,500,3000,xtol=1e-6); print(r, r/B, 10*r/B)
