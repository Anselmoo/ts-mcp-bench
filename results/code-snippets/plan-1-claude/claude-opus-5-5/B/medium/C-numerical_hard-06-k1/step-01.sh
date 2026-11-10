
cat << 'EOF' > /tmp/d6.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
# spin orbitals: (m,s)
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
def ck(k,m1,m2):
    # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) <Y_lm1|Y_k,m1-m2|Y_lm2>
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))*1.0
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in range(-2,3) for b in range(-2,3)}
def two(i,j,k,l,F):  # <ij|1/r|kl>
    (mi,si),(mj,sj),(mk,sk),(ml,sl)=orbs[i],orbs[j],orbs[k],orbs[l]
    if si!=sk or sj!=sl or mi+mj!=mk+ml: return 0.0
    return sum(F[kk]*CK[(kk,mi,mk)]*CK[(kk,ml,mj)] for kk in (0,2,4))
# octahedral one-electron in real basis: eg +6Dq, t2g -4Dq; complex m basis
def hcf(Dq):
    h=np.zeros((5,5))
    # V = Dq*(... ) : diag m=0:6, ±1:-4, ±2:1 ; <2|V|-2>=5
    d={-2:1,-1:-4,0:6,1:-4,2:1}
    for m in d: h[m+2,m+2]=d[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    return h
dets=list(itertools.combinations(range(10),6))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def apply(ops,det):
    # ops: list of (type,orb) applied right to left; returns sign,newdet
    st=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in st: return 0,None
            p=st.index(o); sign*=(-1)**p; st.pop(p)
        else:
            if o in st: return 0,None
            st.insert(0,o); sign*=1
            # sort
            st2=sorted(st); 
            # parity of insertion
            p=st2.index(o); sign*=(-1)**p; st=st2
    return sign,tuple(st)
def build(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5
    F={0:0,2:F2,4:F4}
    H=np.zeros((N,N)); h=hcf(Dq)
    for d in dets:
        for p in d:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=h[orbs[q][0]+2,orbs[p][0]+2]
                if v==0: continue
                s,nd=apply([('c',q),('a',p)],d)
                if s: H[idx[nd],idx[d]]+=s*v
        for k,l in itertools.combinations(d,2):
            for i in range(10):
                for j in range(10):
                    if i==j: continue
                    v=two(i,j,k,l,F)
                    if v==0: continue
                    s,nd=apply([('c',i),('c',j),('a',l),('a',k)],d)
                    if s: H[idx[nd],idx[d]]+=0.5*s*v*2/2
    return H
# precompute pieces linear in Dq,F2,F4
H1=build(1,0,0); HB=build(0,1,0); HC=build(0,0,1)
# Sz=0 subspace and S^2 approx: use Ms=0 dets, identify singlets via S^2
ms=[sum(1 if orbs[o][1]==0 else -1 for o in d) for d in dets]
sel=[i for i in range(N) if ms[i]==0]
# S^2 = S-S+ + Sz^2 + Sz ; build S+
Sp=np.zeros((N,N))
for d in dets:
    for m in range(-2,3):
        p=2*(m+2)+1; q=2*(m+2)
        s,nd=apply([('c',q),('a',p)],d)
        if s: Sp[idx[nd],idx[d]]+=s
S2=Sp.T@Sp
S2=S2[np.ix_(sel,sel)]
def singlets(Dq,B,C):
    H=(Dq*H1+B*HB+C*HC)[np.ix_(sel,sel)]
    H=H+1e5*S2  # push non-singlets up
    w=np.linalg.eigvalsh(H)
    w=w[w<5e4]; w=w-w[0]
    # unique with degeneracy
    out=[]
    for x in w:
        if not out or abs(x-out[-1][0])>1: out.append([x,1])
        else: out[-1][1]+=1
    return out
obs=np.array([16700,26330,35020])
def res(p):
    Dq,B=p; s=singlets(Dq,B,4*B)
    # spin allowed from 1A1: T1 and T2 (deg 3)
    t=[x for x,g in s[1:] if g==3][:3]
    return np.array(t)-obs
print(singlets(2000,600,2400)[:8])
r=least_squares(res,[2000,600]); print(r.x,res(r.x))
EOF
python3 /tmp/d6.py
