import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ml=[2,1,0,-1,-2]
def ck(k,m1,m2):
    # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) * <l m1|Y_k,m1-m2|l m2>
    q=m1-m2
    if abs(q)>k: return 0.0
    # <Y_l m1 | Y_kq | Y_l m2> = int conj(Y_lm1) Y_kq Y_lm2 = (-1)^m1 gaunt(l,k,l,-m1,q,m2)
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m1*gaunt(2,k,2,-m1,q,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ml for b in ml}
so=[(m,s) for m in ml for s in (1,-1)]
dets=[c for c in itertools.combinations(range(10),7)]
idx={d:i for i,d in enumerate(dets)}
def g(i,j,k,l,F):  # <ij|1/r|kl>, i,k electron1
    (mi,si),(mj,sj),(mk,sk),(ml_,sl)=so[i],so[j],so[k],so[l]
    if si!=sk or sj!=sl or mi+mj!=mk+ml_: return 0.0
    return sum(F[kk]*C[(kk,mi,mk)]*C[(kk,ml_,mj)] for kk in (0,2,4))
def Vcf(m1,m2,Dq):
    if m1==m2: return {2:Dq,-2:Dq,1:-4*Dq,-1:-4*Dq,0:6*Dq}[m1]
    if abs(m1-m2)==4: return 5*Dq
    return 0
def build(Dq,B,Cc):
    F4p=Cc/35; F2p=B+5*F4p
    F={0:0.0,2:49*F2p,4:441*F4p}
    n=len(dets); H=np.zeros((n,n))
    # generic second quantization
    def apply(ops,det):
        # ops list of (type,orb) applied right to left
        occ=list(det); sign=1
        for t,o in reversed(ops):
            if t=='a':
                if o not in occ: return None,0
                p=occ.index(o); sign*=(-1)**p; occ.pop(p)
            else:
                if o in occ: return None,0
                occ.append(o); occ.sort(); p=occ.index(o); sign*=(-1)**p
        return tuple(occ),sign
    for d in dets:
        j=idx[d]
        for p in range(10):
            for q in range(10):
                if so[p][1]!=so[q][1]: continue
                v=Vcf(so[p][0],so[q][0],Dq)
                if v==0: continue
                r,s=apply([('c',p),('a',q)],d)
                if r: H[idx[r],j]+=s*v
        for a in d:
          for b in d:
            if a==b: continue
            for p in range(10):
              for q in range(10):
                v=g(p,q,a,b,F)
                if v==0: continue
                r,s=apply([('c',p),('c',q),('a',b),('a',a)],d)
                if r: H[idx[r],j]+=0.5*s*v
    return H
MS=np.array([sum(so[o][1] for o in d) for d in dets])
ML=np.array([sum(so[o][0] for o in d) for d in dets])
def levels(Dq,B,Cc):
    H=build(Dq,B,Cc)
    out={}
    for S2 in (3,1):
        sel=np.where(MS==S2)[0]
        w,v=np.linalg.eigh(H[np.ix_(sel,sel)])
        # remove states with higher S: those also appear at MS=S2+2
        hi=np.where(MS==S2+2)[0]
        whi=np.linalg.eigvalsh(H[np.ix_(hi,hi)]) if len(hi) else np.array([])
        # group
        groups=[];i=0
        while i<len(w):
            j=i
            while j<len(w) and w[j]-w[i]<1e-3: j+=1
            groups.append((w[i],j-i,v[:,i:j]));i=j
        whi=list(whi)
        res=[]
        for e,deg,vec in groups:
            nh=sum(1 for x in whi if abs(x-e)<1e-3)
            if nh==deg: continue
            # character of orbital C4 over subspace minus higher-spin part: compute total trace
            ph=np.exp(1j*np.pi/2*ML[sel])
            tr=np.trace(vec.conj().T@(ph[:,None]*vec)).real
            # subtract higher spin contributions: compute same in hi
            if nh:
                ph2=np.exp(1j*np.pi/2*ML[hi])
                wh,vh=np.linalg.eigh(H[np.ix_(hi,hi)])
                m=np.abs(wh-e)<1e-3
                tr-=np.trace(vh[:,m].conj().T@(ph2[:,None]*vh[:,m])).real
            d=deg-nh
            lab={1:{1:'A1',-1:'A2'}.get(round(tr)),2:'E',3:{1:'T1',-1:'T2'}.get(round(tr))}[d]
            res.append((e,lab))
        out[S2+1]=res
    return out
import sys
L=levels(800,900,3600)
for k in L:
    for e,l in L[k]: print(k,l,round(e,1))
