
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ml=[-2,-1,0,1,2]
orbs=[(m,s) for m in ml for s in (0,1)]
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(5*5)*gaunt(2,k,2,-m1,m1-m2,m2)*np.sqrt(4*np.pi/(2*k+1)))
# <m1|C^k_q|m2> style: c^k(m1,m2)
C={k:{(a,b):ck(k,a,b) for a in ml for b in ml} for k in (0,2,4)}
# two-electron integral <ab|1/r|cd> = sum_k F^k c^k(ma,mc) c^k(md,mb) delta
def U(a,b,c,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=a,b,c,d
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return sum(F[k]*C[k][(ma,mc)]*C[k][(md,mb)] for k in (0,2,4))
dets=list(itertools.combinations(range(10),5))
idx={d:i for i,d in enumerate(dets)}
# crystal field in real basis: oct, eg +6Dq, t2g -4Dq; in complex ml basis
V=np.zeros((5,5))
# Oh: <±2|V|±2>=Dq, <0|V|0>=6Dq, <±1|V|±1>=-4Dq, <2|V|-2>=5Dq
V[0,0]=V[4,4]=1;V[2,2]=6;V[1,1]=V[3,3]=-4;V[0,4]=V[4,0]=5
def apply(ops,det):
    # ops: list of (type,orb) applied right to left; return sign, det
    d=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in d: return 0,None
            p=d.index(o);sign*=(-1)**p;d.pop(p)
        else:
            if o in d: return 0,None
            p=sum(1 for x in d if x<o);sign*=(-1)**p;d.insert(p,o)
    return sign,tuple(d)
def build(Dq,B,Cc):
    F2=49*B+7*Cc; F4=441*Cc/35
    F={0:0,2:F2/49*1,4:F4/441}
    # with c^k normalized gaunt coefficients, need F^k directly
    F={0:0,2:F2,4:F4}
    n=len(dets);H=np.zeros((n,n))
    for j,d in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[ml.index(orbs[p][0]),ml.index(orbs[q][0])]*Dq
                if v==0: continue
                s,nd=apply([('c',p),('a',q)],d)
                if s: H[idx[nd],j]+=s*v
        for p in range(10):
          for q in range(10):
            for r in d:
              for t in d:
                if r>=t: continue
                # 0.5 sum <pq|rt> c+p c+q a_t a_r over all pq, r!=t => sum over r<t with antisym
                val=U(orbs[p],orbs[q],orbs[r],orbs[t],F)-U(orbs[p],orbs[q],orbs[t],orbs[r],F)
                if abs(val)<1e-12 or p==q: continue
                s,nd=apply([('c',p),('c',q),('a',t),('a',r)],d)
                if s: H[idx[nd],j]+=0.5*s*val
    return H
# S^2 for spin label
def S2():
    n=len(dets);M=np.zeros((n,n))
    for j,d in enumerate(dets):
        ms=sum(0.5 if orbs[o][1]==0 else -0.5 for o in d)
        M[j,j]+=ms*ms
        # S-S+ ... S2 = S-S+ + Sz^2 + Sz
        M[j,j]+=ms
        for p in range(10):
          for q in range(10):
            if orbs[p][1]==0 and orbs[q][1]==1 :
              pass
        # S+ = sum c+_{m up} a_{m down}; S- S+
        for m in ml:
          up=orbs.index((m,0));dn=orbs.index((m,1))
          for m2 in ml:
            up2=orbs.index((m2,0));dn2=orbs.index((m2,1))
            s,nd=apply([('c',dn2),('a',up2),('c',up),('a',dn)],d)
            if s: M[idx[nd],j]+=s
    return M
Ssq=S2()
import pickle
def levels(Dq,B,ratio=4.6):
    H=build(Dq,B,ratio*B)
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,ik,kj->j',v,Ssq,v)
    w=w-w[0]
    out=[];
    # group degenerate
    res=[]
    for e,ss in zip(w,s):
        if res and abs(e-res[-1][0])<1e-3: res[-1][2]+=1
        else: res.append([e,ss,1])
    return res,w[0]
r,_=levels(2500,600)
for x in r[:15]: print(round(x[0],1),round(x[1],2),x[2])
EOF
python3 /tmp/d5.py
