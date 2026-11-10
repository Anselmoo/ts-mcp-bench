import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    return float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms if abs(a-b)<=k}
def R(a,b,c,d,F):  # <ab|cd> m-values, ma+mb=mc+md
    if a+b!=c+d: return 0
    return sum(F[k]*CK.get((k,a,c),0)*CK.get((k,d,b),0) for k in (0,2,4))
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,C):
    F={0:0,2:(B+C/7)*49,4:C/35*441}
    V=np.zeros((5,5)); 
    for i,m in enumerate(ms): V[i,i]={0:6,1:-4,2:1}[abs(m)]*Dq
    V[0,4]=V[4,0]=5*Dq
    N=len(dets); H=np.zeros((N,N))
    # one-body
    def apply1(det,p,q): # a_p^+ a_q
        if q not in det: return None
        l=list(det); i=l.index(q); sg=(-1)**i; l.pop(i)
        if p in l: return None
        j=sum(1 for x in l if x<p); l.insert(j,p); sg*=(-1)**j
        return tuple(l),sg
    for d in dets:
        I=idx[d]
        for p in range(10):
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[orbs[p][0]+2,orbs[q][0]+2]
                if v==0: continue
                r=apply1(d,p,q)
                if r: H[idx[r[0]],I]+=r[1]*v
        # two-body 1/2 sum <pq|rs> a+p a+q a_s a_r
        for r_ in d:
          for s_ in d:
            if r_==s_: continue
            for p in range(10):
              for q in range(10):
                if p==q: continue
                if orbs[p][1]!=orbs[r_][1] or orbs[q][1]!=orbs[s_][1]: continue
                v=R(orbs[p][0],orbs[q][0],orbs[r_][0],orbs[s_][0],F)
                if v==0: continue
                t=apply1(d,r_,r_) # identity
                t1=apply1(d,-1,-1) if False else None
                # a_s a_r then a+q a+p
                l=list(d); sg=1
                i=l.index(s_); sg*=(-1)**i; l.pop(i)
                i=l.index(r_); sg*=(-1)**i; l.pop(i)
                if q in l: continue
                j=sum(1 for x in l if x<q); l.insert(j,q); sg*=(-1)**j
                if p in l: continue
                j=sum(1 for x in l if x<p); l.insert(j,p); sg*=(-1)**j
                H[idx[tuple(l)],I]+=0.5*sg*v
    return H
# S^2 and C4 diag
Ms=np.array([sum(0.5 if orbs[o][1]==0 else -0.5 for o in d) for d in dets])
ML=np.array([sum(orbs[o][0] for o in d) for d in dets])
c4=np.exp(1j*np.pi/2*ML)
H0=build(0,0,0)  # check
HD=build(1,0,0)-H0; HB=build(0,1,0)-H0; HC=build(0,0,1)-H0
def levels(Dq,B,C):
    sel=Ms==0.5
    H=(Dq*HD+B*HB+C*HC)[np.ix_(sel,sel)]
    w,v=np.linalg.eigh(H); c=c4[sel]
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-6: j+=1
        tr=np.real(np.sum(np.abs(v[:,i:j])**2*c[:,None]))
        out.append((w[i],j-i,round(tr,2))); i=j
    return out
def names(Dq,B,C):
    # levels with Ms=1/2: quartet appears also in Ms=3/2; deg in Ms=1/2 = orbital deg (each S once)
    sel3=Ms==1.5
    H=(Dq*HD+B*HB+C*HC)[np.ix_(sel3,sel3)]
    q=np.linalg.eigvalsh(H)
    res=[]
    for e,g,tr in levels(Dq,B,C):
        nq=np.sum(abs(q-e)<1e-6)
        sym={1:{1:'A1',-1:'A2'},2:{2:'E'},3:{1:'T1',-1:'T2'}}
        # if quartet+doublet accidental, ignore
        S='4' if nq>0 else '2'
        res.append((e,S+sym.get(g,{}).get(tr,'?%d_%s'%(g,tr))))
    return res
import sys
L=names(-1000 if False else 900,800,3500)
g=L[0][0]
for e,n in L[:12]: print(round(e-g),n)
