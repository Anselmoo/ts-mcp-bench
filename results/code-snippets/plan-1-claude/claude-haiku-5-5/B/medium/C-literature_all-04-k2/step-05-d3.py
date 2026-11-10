import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
n=len(orbs)
ix={m:i for i,m in enumerate(range(-2,3))}
def ck(k,m,q,mp):
    if -m+q+mp!=0: return 0.0
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(l-m)*float(wigner_3j(l,k,l,-m,q,mp))*red
def angular(k,m1,m2,m3,m4):
    return sum((-1)**q*ck(k,m1,q,m3)*ck(k,m2,-q,m4) for q in range(-k,k+1))
V=np.zeros((n,n,n,n,5))
for i,(m1,s1) in enumerate(orbs):
 for j,(m2,s2) in enumerate(orbs):
  for a,(m3,s3) in enumerate(orbs):
   for b,(m4,s4) in enumerate(orbs):
    if s1!=s3 or s2!=s4: continue
    for k in (0,2,4):
        V[i,j,a,b,k]=angular(k,m1,m2,m3,m4)
def apply_ops(ops,state):
    st=list(state); sign=1
    for typ,o in reversed(ops):
        if typ=='a':
            if o not in st: return 0,None
            p=st.index(o); sign*=(-1)**p; st.pop(p)
        else:
            if o in st: return 0,None
            p=sum(1 for x in st if x<o); sign*=(-1)**p; st.insert(p,o)
    return sign,tuple(st)
def build(N,Fk,dq):
    basis=list(itertools.combinations(range(n),N)); idx={b:i for i,b in enumerate(basis)}
    D=len(basis); H=np.zeros((D,D))
    pe=np.zeros((5,5)); pe[ix[0],ix[0]]=1
    v=np.zeros(5); v[ix[2]]+=1; v[ix[-2]]+=1; pe+=np.outer(v,v)/2
    one=dq*(-4*np.eye(5)+10*pe)
    W=sum(Fk[k]*V[:,:,:,:,k] for k in (0,2,4))
    for bi,b in enumerate(basis):
        for i in range(n):
            for j in range(n):
                if orbs[i][1]!=orbs[j][1]: continue
                h=one[ix[orbs[i][0]],ix[orbs[j][0]]]
                if h==0: continue
                s,t=apply_ops([('c',i),('a',j)],b)
                if s: H[idx[t],bi]+=h*s
        for i in range(n):
          for j in range(n):
            for a in range(n):
              for c in range(n):
                w=W[i,j,a,c]
                if abs(w)<1e-14: continue
                s,t=apply_ops([('c',i),('c',j),('a',c),('a',a)],b)
                if s: H[idx[t],bi]+=0.5*w*s
    return basis,H
