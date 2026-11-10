cd /tmp; python3 - << 'EOF'
import numpy as np, itertools, math
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*math.sqrt(4*math.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
def sortsign(arr):
    arr=arr[:]; s=1
    for x in range(len(arr)):
        for y in range(len(arr)-1-x):
            if arr[y]>arr[y+1]: arr[y],arr[y+1]=arr[y+1],arr[y]; s=-s
    return tuple(arr),s
def sz(d): return sum(1 if so[x][1]==0 else -1 for x in d)
def sector(S2):
    dets=[d for d in itertools.combinations(range(10),4) if sz(d)==S2]
    idx={d:i for i,d in enumerate(dets)}
    N=len(dets)
    Hd=np.zeros((N,N)); Hk={k:np.zeros((N,N)) for k in (2,4)}
    for i,d in enumerate(dets):
        occ=list(d)
        for p_i,p in enumerate(occ):
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                mp,mq=so[p][0],so[q][0]
                v={-2:1,-1:-4,0:6,1:-4,2:1}[mp] if mp==mq else (5 if abs(mp-mq)==4 else 0)
                if v==0: continue
                if q!=p and q in occ: continue
                new=occ.copy(); new[p_i]=q
                t,s=sortsign(new); Hd[idx[t],i]+=s*v
        for (ia,a),(ib,b) in itertools.combinations(enumerate(occ),2):
            rest=[x for x in occ if x not in (a,b)]
            for c in range(10):
                for e in range(10):
                    if c==e or c in rest or e in rest: continue
                    if so[c][1]!=so[a][1] or so[e][1]!=so[b][1]: continue
                    m1,m2,m3,m4=so[c][0],so[e][0],so[a][0],so[b][0]
                    if m1+m2!=m3+m4: continue
                    new=occ.copy(); new[ia]=c; new[ib]=e
                    t,s=sortsign(new)
                    for k in (2,4):
                        Hk[k][idx[t],i]+=s*CK[(k,m1,m3)]*CK[(k,m4,m2)]
    return Hd,Hk
S={s:sector(s) for s in (0,2,4)}
def eig(s,Dq,B,C):
    Hd,Hk=S[s]; F2=49*B+7*C; F4=63*C/5
    H=Dq*Hd+F2*Hk[2]+F4*Hk[4]; H=(H+H.T)/2
    return np.linalg.eigvalsh(H)
def triplets(Dq,B,C):
    e1=list(eig(2,Dq,B,C)); e2=eig(4,Dq,B,C)
    for x in e2:
        j=np.argmin([abs(y-x) for y in e1]); e1.pop(j)
    e1=np.array(e1); e0=eig(0,Dq,B,C)
    # group degeneracies
    out=[];
    for x in sorted(e1):
        if out and abs(x-out[-1][0])<1e-4: out[-1][1]+=1
        else: out.append([x,1])
    return out,e0.min(),e2.min()
import sys
t,g0,g5=triplets(2500,600,4.7*600)
print([(round(a-t[0][0]),n) for a,n in t[:10]], round(g5-t[0][0]), round(g0-t[0][0]))
obs=np.array([18850,19750,20560])
def res(p):
    Dq,B=p; t,_,_=triplets(Dq,B,4.7*B)
    ex=np.array([a-t[0][0] for a,n in t[1:4]]); return ex-obs
for g in [(2000,500),(2500,700),(3000,600),(2200,300)]:
    r=least_squares(res,g); print(r.x, r.fun)
    t,g0,g5=triplets(r.x[0],r.x[1],4.7*r.x[1])
    print([(round(a-t[0][0]),n) for a,n in t[:8]], round(g5-t[0][0]))
EOF