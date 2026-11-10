import numpy as np, itertools, sys
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
def c(k,m1,m2):
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m1*gaunt(2,k,2,-m1,m1-m2,m2))
C2={(a,b,k):c(k,orbs[a][0],orbs[b][0]) for a in range(10) for b in range(10) for k in (2,4)}
def ap(op,st,dag):
    if dag:
        if op in st: return None
        pos=sum(1 for x in st if x<op); return tuple(sorted(st+(op,))),(-1)**pos
    if op not in st: return None
    pos=st.index(op); return tuple(x for x in st if x!=op),(-1)**pos
def build(MS):
    states=[s for s in itertools.combinations(range(10),7) if sum(1 if o%2==0 else -1 for o in s)==MS]
    idx={s:i for i,s in enumerate(states)}; n=len(states)
    def one(i,j):
        M=np.zeros((n,n))
        for st in states:
            r=ap(j,st,False)
            if r is None: continue
            s2,p=r; r=ap(i,s2,True)
            if r is None: continue
            M[idx[r[0]],idx[st]]+=p*r[1]
        return M
    hd=np.zeros((n,n))
    for m,v in {2:1,-2:1,1:-4,-1:-4,0:6}.items():
        for s in (0,1):
            i=2*(m+2)+s; hd+=v*one(i,i)
    for s in (0,1): hd+=5*(one(8+s,s)+one(s,8+s))
    def two(k):
        M=np.zeros((n,n))
        for a in range(10):
         for b in range(10):
          for cc in range(10):
           for d in range(10):
            (m1,s1),(m2,s2),(m3,s3),(m4,s4)=orbs[a],orbs[b],orbs[cc],orbs[d]
            if not(s1==s3 and s2==s4 and m1+m2==m3+m4 and a!=b and cc!=d): continue
            v=C2[(a,cc,k)]*C2[(d,b,k)]
            if abs(v)<1e-14: continue
            for st in states:
                x=ap(cc,st,False)
                if not x: continue
                s1_,p1=x; x=ap(d,s1_,False)
                if not x: continue
                x2,p2=x; x=ap(b,x2,True)
                if not x: continue
                x3,p3=x; x=ap(a,x3,True)
                if not x: continue
                M[idx[x[0]],idx[st]]+=0.5*v*p1*p2*p3*x[1]
        return M
    return hd,two(2),two(4)
def groups(e,tol=1e-3):
    out=[]
    for x in e:
        if out and abs(x-out[-1][0])<tol: out[-1][1]+=1
        else: out.append([x,1])
    return out
D={ms:build(ms) for ms in (1,3)}
st1=[s for s in itertools.combinations(range(10),7) if sum(1 if o%2==0 else -1 for o in s)==1]
M1=np.array([sum(orbs[o][0] for o in s) for s in st1])
ph=np.exp(-1j*np.pi/2*M1)
def lev(Dq,B,C):
    hd,T2,T4=D[3]; e3=np.linalg.eigvalsh(Dq*hd+(49*B+7*C)*T2+(63*C/5)*T4)
    hd,T2,T4=D[1]; e,v=np.linalg.eigh(Dq*hd+(49*B+7*C)*T2+(63*C/5)*T4)
    qs=[g[0] for g in groups(e3-e3.min())]
    e=e-e.min()
    i=0;res=[]
    for x,dg in groups(e):
        V=v[:,i:i+dg]; chi=sum((abs(V[:,k])**2*ph).sum() for k in range(dg)).real; i+=dg
        res.append((x,dg,chi,any(abs(x-y)<1e-2 for y in qs)))
    return qs,res
def dbl(res):
    return [r[0] for r in res if not r[3] and r[1]==3 and abs(r[2]-1)<.1]
def qfit(C):
    g=lambda p:[lev(p[0],p[1],C)[0][1]-8100,lev(p[0],p[1],C)[0][3]-19400]
    s=least_squares(g,(900,850),x_scale=[100,100]);return s.x
for C in [3000,3500,4000,4500,5000,6000,7000]:
    Dq,B=qfit(C);qs,res=lev(Dq,B,C);print(C,round(Dq),round(B),[round(x) for x in qs],[round(x) for x in dbl(res)][:3])
