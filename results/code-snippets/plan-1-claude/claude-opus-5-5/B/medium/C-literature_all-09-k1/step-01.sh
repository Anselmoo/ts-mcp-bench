
pip list 2>/dev/null | grep -i -E "sympy|numpy|scipy" ; cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
l=2; ms=range(-2,3)
# real-space via complex orbitals; CF in complex basis
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(5*5)*0+0)
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2): # <l m1|C^k_{m1-m2}|l m2>
    q=m1-m2
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
C={}
for k in (0,2,4):
  for a in ms:
    for b in ms: C[(k,a,b)]=c(k,a,b)
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),5))
idx={d:i for i,d in enumerate(dets)}
# CF octahedral: Dq in complex basis: V = Dq*(6 for m=0, -4 for m=±1, 1 for ±2 diag, 5 between ±2)
def cfmat(Dq):
    V=np.zeros((5,5))
    for i,m in enumerate(ms):
        V[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    return V
def build(Dq,B,Cr):
    F0=0;F2=49*B+7*Cr;F4=441*Cr/35
    F={0:F0,2:F2,4:F4}
    V=cfmat(Dq); N=len(dets); H=np.zeros((N,N))
    for d in dets:
        i=idx[d]
        # one-body
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=V[ms.index(so[q][0]),ms.index(so[p][0])]
                if v==0: continue
                if q!=p and q in d: continue
                new=list(d); pos=new.index(p); new[pos]=q
                sign=(-1)**pos; srt=sorted(new)
                # permutation sign
                perm=np.argsort(new); 
                s=np.linalg.det(np.eye(5)[perm]) 
                # put q at position pos then sort
                tmp=list(d); tmp.pop(pos); 
                sign=(-1)**pos; k=sum(1 for x in tmp if x<q); sign*=(-1)**k
                H[idx[tuple(srt)],i]+=sign*v
        # two-body
        for a,b in itertools.combinations(d,2):
            for cc in range(10):
              for dd in range(10):
                if cc==dd: continue
                (m1,s1),(m2,s2)=so[a],so[b];(m3,s3),(m4,s4)=so[cc],so[dd]
                if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: continue
                val=sum(F[k]*C[(k,m3,m1)]*C[(k,m2,m4)] for k in (0,2,4))
                if val==0: continue
                # a^+_c a^+_d a_b a_a |d>
                occ=list(d); sg=1
                for x in (a,b):
                    p=occ.index(x); sg*=(-1)**p; occ.pop(p)
                ok=True
                for x in (dd,cc):
                    if x in occ: ok=False;break
                    p=sum(1 for y in occ if y<x); sg*=(-1)**p; occ.insert(p,x)
                if not ok: continue
                H[idx[tuple(occ)],i]+=sg*val
    return H
# S^2
def S2():
    N=len(dets);M=np.zeros((N,N))
    for d in dets:
        i=idx[d]; sz=sum(0.5 if so[p][1]==0 else -0.5 for p in d)
        M[i,i]+=sz*sz-sz
        # S+S-: S- lowers
        for p in d:
          if so[p][1]!=0: continue
          q=p+1
          if q in d: continue
          occ=list(d);pos=occ.index(p);sg=(-1)**pos;occ.pop(pos);k=sum(1 for y in occ if y<q);sg*=(-1)**k;occ.insert(k,q)
          d2=tuple(occ)
          for p2 in d2:
            if so[p2][1]!=1: continue
            q2=p2-1
            if q2 in d2: continue
            o=list(d2);pp=o.index(p2);s2=(-1)**pp;o.pop(pp);kk=sum(1 for y in o if y<q2);s2*=(-1)**kk;o.insert(kk,q2)
            M[idx[tuple(o)],i]+=sg*s2
    return M
SS=S2()
def levels(Dq,B,Cr):
    H=build(Dq,B,Cr)
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,jk,ki->i',v.T,SS,v)
    out=[(round(x,3),round(si,2)) for x,si in zip(w,s)]
    gs=w[0]
    q=sorted(set(round(x-gs,2) for x,si in zip(w,s) if abs(si-3.75)<0.1))
    return gs,q,w,s
gs,q,w,s=levels(0,800,3200); print(q[:5], 10*800+5*3200)
gs,q,w,s=levels(800,800,3200); print(q[:6])
np.save('/tmp/ok',1)
import pickle; pickle.dump(None,open('/tmp/x','wb'))
def res(x):
    Dq,B,Cr=x
    gs,q,w,s=levels(Dq,B,Cr)
    return [q[0]-19720,q[1]-23260,q[2]-24980]
r=least_squares(res,[800,800,3200]); print(r.x, res(r.x)); print(levels(*r.x)[1][:6])
EOF
python3 /tmp/d5.py
