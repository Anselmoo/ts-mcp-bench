python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in range(-2,3) for b in range(-2,3)}
def two(i,j,k,l,F):
    (mi,si),(mj,sj),(mk,sk),(ml,sl)=orbs[i],orbs[j],orbs[k],orbs[l]
    if si!=sk or sj!=sl or mi+mj!=mk+ml: return 0.0
    return sum(F[kk]*CK[(kk,mi,mk)]*CK[(kk,ml,mj)] for kk in (2,4))
def hcf(Dq):
    h=np.zeros((5,5)); d={-2:1,-1:-4,0:6,1:-4,2:1}
    for m in d: h[m+2,m+2]=d[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    return h
dets=list(itertools.combinations(range(10),6)); idx={d:i for i,d in enumerate(dets)}; N=len(dets)
def apply(ops,det):
    st=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in st: return 0,None
            p=st.index(o); sign*=(-1)**p; st.pop(p)
        else:
            if o in st: return 0,None
            st2=sorted(st+[o]); p=st2.index(o); sign*=(-1)**p; st=st2
    return sign,tuple(st)
def build(Dq,B,C):
    F={2:49*B+7*C,4:63*C/5}
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
                    if s: H[idx[nd],idx[d]]+=s*v
    return H
H1=build(1,0,0); HB=build(0,1,0); HC=build(0,0,1)
print(np.allclose(HB,HB.T))
ms=[sum(1 if orbs[o][1]==0 else -1 for o in d) for d in dets]
sel=[i for i in range(N) if ms[i]==0]
Sp=np.zeros((N,N))
for d in dets:
    for m in range(-2,3):
        s,nd=apply([('c',2*(m+2)),('a',2*(m+2)+1)],d)
        if s: Sp[idx[nd],idx[d]]+=s
S2=(Sp.T@Sp)[np.ix_(sel,sel)]
def singlets(Dq,B,C):
    H=(Dq*H1+B*HB+C*HC)[np.ix_(sel,sel)]+1e6*S2
    w=np.linalg.eigvalsh(H); w=w[w<5e5]; w=w-w[0]
    out=[]
    for x in w:
        if not out or abs(x-out[-1][0])>1: out.append([x,1])
        else: out[-1][1]+=1
    return out
# free ion check
print([(round(x/600,3),g) for x,g in singlets(0,600,2400)][:6])
obs=np.array([16700,26330,35020])
def res(p):
    Dq,B=p; s=singlets(Dq,B,4*B)
    t=[x for x,g in s[1:] if g==3][:3]
    return np.array(t)-obs
for g in ([2000,600],[2500,500],[2200,700]):
    r=least_squares(res,g); print(r.x,res(r.x))
print(singlets(*r.x,4*r.x[1])[:10])
EOF