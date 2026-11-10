import numpy as np, itertools
from sympy.physics.wigner import gaunt
ml=[2,1,0,-1,-2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m1*gaunt(2,k,2,-m1,q,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ml for b in ml}
so=[(m,s) for m in ml for s in (1,-1)]
dets=[c for c in itertools.combinations(range(10),7)]
idx={d:i for i,d in enumerate(dets)}
def apply(ops,det):
    occ=list(det); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in occ: return None,0
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None,0
            occ.insert(0,o); p=0
            # move to sorted position
            occ.sort(); p=occ.index(o); sign*=(-1)**p
    return tuple(occ),sign
n=len(dets)
def mats():
    # return matrices for Dq=1, F2=1, F4=1 separately
    M={'Dq':np.zeros((n,n)),2:np.zeros((n,n)),4:np.zeros((n,n))}
    cf={2:1,-2:1,1:-4,-1:-4,0:6}
    for d in dets:
        j=idx[d]
        for p in range(10):
            for q in range(10):
                if so[p][1]!=so[q][1]: continue
                m1,m2=so[p][0],so[q][0]
                v=cf[m1] if m1==m2 else (5 if abs(m1-m2)==4 else 0)
                if v==0: continue
                r,s=apply([('c',p),('a',q)],d)
                if r: M['Dq'][idx[r],j]+=s*v
        for a in d:
          for b in d:
            if a==b: continue
            for p in range(10):
              for q in range(10):
                (mi,si),(mj,sj),(mk,sk),(mm,sl)=so[p],so[q],so[a],so[b]
                if si!=sk or sj!=sl or mi+mj!=mk+mm: continue
                r,s=apply([('c',p),('c',q),('a',b),('a',a)],d)
                if not r: continue
                for kk in (2,4):
                    M[kk][idx[r],j]+=0.5*s*C[(kk,mi,mk)]*C[(kk,mm,mj)]
    return M
import pickle,os
if os.path.exists('M.pkl'): M=pickle.load(open('M.pkl','rb'))
else: M=mats(); pickle.dump(M,open('M.pkl','wb'))
MS=np.array([sum(so[o][1] for o in d) for d in dets])
ML=np.array([sum(so[o][0] for o in d) for d in dets])
def build(Dq,B,Cc):
    F4p=Cc/35; F2p=B+5*F4p
    return Dq*M['Dq']+49*F2p*M[2]+441*F4p*M[4]
def levels(Dq,B,Cc):
    H=build(Dq,B,Cc); out={}
    for S2 in (3,1):
        sel=np.where(MS==S2)[0]
        w,v=np.linalg.eigh(H[np.ix_(sel,sel)])
        hi=np.where(MS==S2+2)[0]
        wh,vh=np.linalg.eigh(H[np.ix_(hi,hi)]) if len(hi) else (np.array([]),None)
        ph=np.exp(1j*np.pi/2*ML[sel])
        res=[];i=0
        while i<len(w):
            j=i
            while j<len(w) and w[j]-w[i]<1e-4*max(1,abs(w[i]))+1e-3: j+=1
            e=w[i];deg=j-i;vec=v[:,i:j]
            tr=np.trace(vec.conj().T@(ph[:,None]*vec)).real
            m=np.abs(wh-e)<1e-3 if len(wh) else np.array([],bool)
            nh=int(m.sum())
            if nh:
                ph2=np.exp(1j*np.pi/2*ML[hi])
                tr-=np.trace(vh[:,m].conj().T@(ph2[:,None]*vh[:,m])).real
            dd=deg-nh
            if dd>0:
                lab={1:{1:'A1',-1:'A2'}.get(round(tr),'?'),2:'E',3:{1:'T1',-1:'T2'}.get(round(tr),'?')}.get(dd,'?%d'%dd)
                res.append((e,lab))
            i=j
        out[S2+1]=res
    return out
if __name__=='__main__':
    L=levels(800,900,3600)
    for k in L:
        for e,l in L[k]: print(k,l,round(e,1))
