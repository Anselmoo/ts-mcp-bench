python3 - << 'EOF' 2>&1 | tail -5
import numpy as np, itertools, math
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float(gaunt(2,k,2,-m1,q,m2))*(-1)**m1*math.sqrt(4*math.pi/(2*k+1))
C={k:{(a,b):ck(k,a,b) for a in ms for b in ms} for k in (0,2,4)}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3)); idx={d:i for i,d in enumerate(dets)}
def apply(ops,det):
    st=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in st: return 0,None
            p=st.index(o);sign*=(-1)**p;st.pop(p)
        else:
            if o in st: return 0,None
            p=sum(1 for x in st if x<o);sign*=(-1)**p;st.insert(p,o)
    return sign,tuple(st)
N=len(dets)
def mats():
    HV=np.zeros((N,N));HF={k:np.zeros((N,N)) for k in (2,4)}
    V=np.zeros((5,5))
    for i,m in enumerate(ms): V[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]
    V[0,4]=V[4,0]=5
    for j,d in enumerate(dets):
        for a in range(10):
            for b in range(10):
                if so[a][1]==so[b][1]:
                    v=V[ms.index(so[a][0]),ms.index(so[b][0])]
                    if v:
                        s,nd=apply([('c',a),('a',b)],d)
                        if s: HV[idx[nd],j]+=s*v
        for p in range(10):
         for q in range(10):
          for r in d:
           for t in d:
            if so[p][1]!=so[r][1] or so[q][1]!=so[t][1]: continue
            m1,m2,m3,m4=so[p][0],so[q][0],so[r][0],so[t][0]
            if m1+m2!=m3+m4: continue
            s,nd=apply([('c',p),('c',q),('a',t),('a',r)],d)
            if not s: continue
            for k in (2,4):
                HF[k][idx[nd],j]+=0.5*s*C[k][(m1,m3)]*C[k][(m4,m2)]
    return HV,HF
HV,HF=mats()
def levels(Dq,B,Cc):
    H=Dq*HV+49*(B+Cc/7)*HF[2]+441*Cc/35*HF[4]
    e=np.linalg.eigvalsh(H);e=e-e[0];u=[]
    for x in e:
        if not u or x-u[-1][0]>1.0: u.append([round(x,1),1])
        else: u[-1][1]+=1
    return u
print(levels(1417,878,3500)[:8])
from scipy.optimize import brentq
f=lambda Cc: levels(1417,878,Cc)[2][0]-18540
Cs=brentq(f,2000,6000,xtol=0.01); print(Cs, Cs/878, levels(1417,878,Cs)[:7])
EOF