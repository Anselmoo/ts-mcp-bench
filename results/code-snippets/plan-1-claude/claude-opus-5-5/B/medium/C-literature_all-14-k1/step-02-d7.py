import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import fsolve
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (1,-1)]
def ck(k,m1,m2): return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
Ck={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
dets=list(itertools.combinations(range(10),7)); idx={d:i for i,d in enumerate(dets)}; N=len(dets)
def annih(st,i):
    if i not in st: return None,0
    p=st.index(i); return st[:p]+st[p+1:],(-1)**p
def create(st,i):
    if i in st: return None,0
    l=list(st); p=sum(1 for x in l if x<i); l.insert(p,i); return tuple(l),(-1)**p
def op(st,cr,an):
    s=1
    for i in an:
        st,f=annih(st,i); 
        if st is None: return None,0
        s*=f
    for i in cr:
        st,f=create(st,i)
        if st is None: return None,0
        s*=f
    return st,s
H1=np.zeros((N,N)); H2={2:np.zeros((N,N)),4:np.zeros((N,N))}
def h1(m1,m2):
    if m1==m2: return {0:6,1:-4,-1:-4,2:1,-2:1}[m1]
    if abs(m1-m2)==4: return 5
    return 0
for j,d in enumerate(dets):
    for p in range(10):
        for q in range(10):
            if orbs[p][1]!=orbs[q][1]: continue
            v=h1(orbs[p][0],orbs[q][0])
            if v==0: continue
            st,s=op(d,[p],[q])
            if st: H1[idx[st],j]+=v*s
    # 1/2 sum <pq|rs> a+p a+q a s a r
    for r in d:
        for s_ in d:
            if r==s_: continue
            for p in range(10):
                for q in range(10):
                    (mp,sp),(mq,sq),(mr,sr),(msx,ss)=orbs[p],orbs[q],orbs[r],orbs[s_]
                    if sp!=sr or sq!=ss or mp+mq!=mr+msx: continue
                    st,sg=op(d,[q,p],[r,s_])  # a+p a+q a_s a_r : apply a_r first? order: rightmost first
                    if st is None: continue
                    for k in (2,4):
                        H2[k][idx[st],j]+=0.5*sg*Ck[(k,mp,mr)]*Ck[(k,msx,mq)]
# S^2 and ML
ML=np.array([sum(orbs[i][0] for i in d) for d in dets])
Sz=np.array([sum(orbs[i][1] for i in d)/2 for d in dets])
Sp=np.zeros((N,N))
for j,d in enumerate(dets):
    for m in ms:
        up=ms.index(m)*2; dn=up+1
        st,s=op(d,[up],[dn])
        if st: Sp[idx[st],j]+=s
S2=Sp.T@Sp+np.diag(Sz**2-Sz)  # S-S+ + Sz^2+Sz ... use S+S- = S-S+... check
S2=Sp@Sp.T+np.diag(Sz**2-Sz)
def levels(Dq,B,C):
    F2=49*(B+C/7); F4=441*C/35
    H=Dq*H1+F2/49*H2[2]+F4/441*H2[4]
    # the k operators use F^k; Ck product times F^k
    H=Dq*H1+F2*H2[2]+F4*H2[4]
    e,v=np.linalg.eigh(H)
    out=[];i=0
    while i<N:
        j=i
        while j<N and e[j]-e[i]<1e-6: j+=1
        V=v[:,i:j]; s2=np.trace(V.T@S2@V)/(j-i); S=(-1+np.sqrt(1+4*s2))/2
        c4=np.real(np.sum(np.abs(V)**2*np.exp(-1j*ML*np.pi/2)[:,None]))/(2*S+1)
        out.append((e[i],j-i,round(2*S+1),round(c4,2))); i=j
    e0=out[0][0]
    return [(round(a-e0,1),b,c,d) for a,b,c,d in out]
import pickle
for l in levels(810,900,3600)[:25]: print(l)
