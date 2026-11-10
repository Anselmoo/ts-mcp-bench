
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ml=[-2,-1,0,1,2]
def ck(k,m1,m2): # <l m1|C^k|l m2>, l=2
    from sympy.physics.wigner import wigner_3j
    q=m1-m2
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ml for b in ml if abs(a-b)<=k}
def cc(k,a,b): return C.get((k,a,b),0.0)
# V[a,b,c,d]=<ab|1/r12|cd> = sum_k F_k c^k(a,c)c^k(b,d) delta(a+b,c+d), c^k(a,c)=<a|Ck|c> ; 
def Vint(F,a,b,c,d):
    if a+b!=c+d: return 0
    return sum(F[k]*cc(k,a,c)*cc(k,d,b)*1 for k in (2,4)) # <ab|cd>: c^k(a,c)c^k(d,b)
orbs=[(m,s) for m in ml for s in (0,1)]
dets=[c for c in itertools.combinations(range(10),6)]
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,Cc):
    F={2:49*B+7*Cc,4:63*Cc/5}
    # one-body
    s2=1/np.sqrt(2)
    eg=[np.zeros(5),np.zeros(5)]
    v0=np.zeros(5);v0[2]=1
    v1=np.zeros(5);v1[4]=s2;v1[0]=s2
    P=6*Dq*(np.outer(v0,v0)+np.outer(v1,v1))
    t=[np.zeros(5,complex) for _ in range(3)]
    t[0][4]=s2/1j;t[0][0]=-s2/1j  # xy
    t[1][3]=1;t[2][1]=1
    P=P-4*Dq*sum(np.outer(x,x.conj()) for x in t)
    h=np.zeros((10,10),complex)
    for i,(m,s) in enumerate(orbs):
        for j,(n,r) in enumerate(orbs):
            if s==r:h[i,j]=P[m+2,n+2]
    # two body antisym matrix elements g[i,j,k,l]=<ij|kl>
    g=np.zeros((10,10,10,10))
    for i,(a,s1) in enumerate(orbs):
     for j,(b,s2_) in enumerate(orbs):
      for k,(c,s3) in enumerate(orbs):
       for l,(d,s4) in enumerate(orbs):
        if s1==s3 and s2_==s4: g[i,j,k,l]=Vint(F,a,b,c,d)
    H=np.zeros((len(dets),)*2,complex)
    def apply_ann(d,o):
        if o not in d:return None
        p=d.index(o);return tuple(x for x in d if x!=o),(-1)**p
    def apply_cre(d,o):
        if o in d:return None
        l=sorted(d+(o,));return tuple(l),(-1)**l.index(o)
    for I,d in enumerate(dets):
        for i in range(10):
            for j in range(10):
                if abs(h[i,j])<1e-12:continue
                r=apply_ann(d,j)
                if not r:continue
                d1,s=r;r=apply_cre(d1,i)
                if not r:continue
                H[idx[r[0]],I]+=h[i,j]*s*r[1]
        # two body 1/2 sum g_ijkl a†i a†j a_l a_k
        for k in d:
         for l in d:
          if k==l:continue
          r=apply_ann(d,k);d1,s1=r
          r=apply_ann(d1,l);d2,s2=r
          for i in range(10):
           for j in range(10):
            v=g[i,j,k,l]
            if v==0:continue
            r=apply_cre(d2,j)
            if not r:continue
            d3,s3=r;r=apply_cre(d3,i)
            if not r:continue
            H[idx[r[0]],I]+=0.5*v*s1*s2*s3*r[1]
    return H
# S^2
def S2():
    M=np.zeros((len(dets),)*2)
    for I,d in enumerate(dets):
        sz=sum(0.5 if o%2==0 else -0.5 for o in d)
        M[I,I]+=sz*sz
        # S-S+ ... S2=S-S+ + Sz + Sz^2
        M[I,I]+=sz
        for m in ml:
            a=2*(m+2);b=a+1 # a up, b down
            pass
        # S- S+ : sum_{p,q} a†_pdown a_pup a†_qup a_qdown
        for p in ml:
          for q in ml:
            pu,pd,qu,qd=[2*(x+2)+y for x,y in((p,0),(p,1),(q,0),(q,1))]
            cur=d;sg=1
            if qd not in cur: continue
            p_=cur.index(qd);sg*=(-1)**p_;cur=tuple(x for x in cur if x!=qd)
            if qu in cur: continue
            l=sorted(cur+(qu,));sg*=(-1)**l.index(qu);cur=tuple(l)
            if pu not in cur: continue
            p_=cur.index(pu);sg*=(-1)**p_;cur=tuple(x for x in cur if x!=pu)
            if pd in cur: continue
            l=sorted(cur+(pd,));sg*=(-1)**l.index(pd);cur=tuple(l)
            M[idx[cur],I]+=sg
    return M
S=S2()
# restrict to Sz=0 dets
sel=[i for i,d in enumerate(dets) if sum(1 for o in d if o%2==0)==3]
S=S[np.ix_(sel,sel)]
def spec(Dq,B,Cc):
    H=build(Dq,B,Cc)[np.ix_(sel,sel)]
    # simultaneous diag
    w,v=np.linalg.eigh(H+0.001*S)
    s=np.real(np.einsum('ij,ik,kj->j',v.conj(),S,v))
    e=np.real(np.einsum('ij,ik,kj->j',v.conj(),H,v))
    sing=sorted(e[s<0.3]);return np.array(sing)
import sys
def levels(Dq,B):
    sg=spec(Dq,B,4.5*B)
    g=sg[0]
    # distinct levels
    u=[];
    for x in sg-g:
        if not u or abs(x-u[-1][0])>1:u.append([x,1])
        else:u[-1][1]+=1
    return u
print(levels(2000/10*1.0*10/ 10,600)[:8])
obs=np.array([13960,22740,29700])
def res(p):
    u=levels(*p); 
    # T1,T2 degeneracy 3 (singlet levels)
    t=[x for x,n in u if n==3][:3]
    return np.array(t)-obs
for g in [(2000,400),(2500,500),(1800,450)]:
    r=least_squares(res,g);print(r.x,r.fun,levels(*r.x)[:8])
E
python3 /tmp/a.py
