cat << 'EOF' | python3
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
n=10
cache={}
def c(k,m,mp,q):
    if m-mp!=q: return 0.0
    key=(k,m,mp,q)
    if key not in cache:
        cache[key]=float((-1)**(l-m)*float(wigner_3j(l,k,l,-m,q,mp))*(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0)))
    return cache[key]
states=list(itertools.combinations(range(n),8))
idx={s:i for i,s in enumerate(states)}
mm=lambda p: orbs[p][0]
sp=lambda p: orbs[p][1]
Mcf=np.zeros((5,5))
Mcf[1,1]=Mcf[3,3]=-4; Mcf[2,2]=6; Mcf[0,0]=Mcf[4,4]=1; Mcf[0,4]=Mcf[4,0]=5
H1=np.zeros((n,n))
for p in range(n):
    for q in range(n):
        if sp(p)==sp(q): H1[p,q]=Mcf[mm(p)+2,mm(q)+2]
def op_one(hm):
    Hs=np.zeros((len(states),)*2)
    for i,st in enumerate(states):
        occ=set(st)
        for q in occ:
            for p in range(n):
                if hm[p,q]==0: continue
                o2=set(occ); sg=(-1)**sum(1 for x in occ if x<q); o2.remove(q)
                if p in o2: continue
                sg*=(-1)**sum(1 for x in o2 if x<p); o2.add(p)
                Hs[idx[tuple(sorted(o2))],i]+=hm[p,q]*sg
    return Hs
def op_two(Vt):
    Hs=np.zeros((len(states),)*2)
    for i,st in enumerate(states):
        occ=set(st)
        for r in occ:
            for s in occ:
                if r==s: continue
                for p in range(n):
                    for q in range(n):
                        v=Vt[p,q,r,s]
                        if v==0 or p==q: continue
                        o2=set(occ)
                        sg=(-1)**sum(1 for x in o2 if x<r); o2.remove(r)
                        sg*=(-1)**sum(1 for x in o2 if x<s); o2.remove(s)
                        if p in o2 or q in o2: continue
                        sg*=(-1)**sum(1 for x in o2 if x<q); o2.add(q)
                        sg*=(-1)**sum(1 for x in o2 if x<p); o2.add(p)
                        Hs[idx[tuple(sorted(o2))],i]+=0.5*v*sg
    return Hs
def Vpart(k):
    Vt=np.zeros((n,n,n,n))
    for p,q,r,s in itertools.product(range(n),repeat=4):
        if sp(p)==sp(r) and sp(q)==sp(s):
            Vt[p,q,r,s]=sum(c(k,mm(p),mm(r),qq)*c(k,mm(q),mm(s),-qq)*(-1)**qq for qq in range(-k,k+1))
    return Vt
T2=op_two(Vpart(2)); T4=op_two(Vpart(4))
One=op_one(H1)
Sz=np.array([0.5*(sum(1 for x in st if sp(x)==0)-sum(1 for x in st if sp(x)==1)) for st in states])
Sp=np.zeros((len(states),)*2)
for i,st in enumerate(states):
    occ=set(st)
    for m in range(-2,3):
        pu=orbs.index((m,0)); pd=orbs.index((m,1))
        if pd in occ and pu not in occ:
            o2=set(occ); sg=(-1)**sum(1 for x in occ if x<pd); o2.remove(pd)
            sg*=(-1)**sum(1 for x in o2 if x<pu); o2.add(pu)
            Sp[idx[tuple(sorted(o2))],i]+=sg
S2=Sp.T@Sp+np.diag(Sz)+np.diag(Sz**2)
def spectrum(Dq,B,C):
    F4=12.6*C; F2=49*B+7*C
    H=Dq*One+F2*T2+F4*T4
    ev,vec=np.linalg.eigh(H+1e5*S2)
    s2=np.einsum('ij,ik,kj->j',vec,S2,vec)
    trip=np.array(sorted([e for e,s in zip(ev,s2) if s>1]))-2e5
    sing=np.array(sorted([e for e,s in zip(ev,s2) if s<1]))
    return trip,sing
def groups(x,tol=1e-6):
    out=[]
    for v in x:
        if out and abs(v-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([float(v),1])
    return out
def levels(p):
    Dq,B,C=p
    t,s=spectrum(Dq,B,C)
    tg=groups(t); sg=groups(s)
    g0=tg[0][0]
    trip=[v-g0 for v,k in tg if k>=9]
    Es=[v-g0 for v,k in sg if k==2]
    return trip,Es
obs=dict(T2=7400,T1F=12660,T1P=23840,E=15150)
def resid(p,which):
    trip,Es=levels(p)
    if len(trip)<3 or len(Es)<1: return np.ones(4)*1e4
    r=[10*p[0]-obs['T2'], trip[1]-obs['T1F'], trip[2]-obs['T1P'], Es[which]-obs['E'] if len(Es)>which else 1e4]
    return np.array(r)
res={}
for which in (0,1):
    best=None
    for B0 in (700,900,1100):
        for C0 in (3000,4000,5000):
            sol=least_squares(lambda p: resid(p,which),[740,B0,C0],x_scale=[100,500,1000],diff_step=1e-4)
            if best is None or sol.cost<best.cost: best=sol
    res[which]=best
    print("E choice",which,"Dq,B,C=",np.round(best.x,2),"resid",np.round(best.fun,2),"cost",best.cost)
    print("levels",levels(best.x))
EOF