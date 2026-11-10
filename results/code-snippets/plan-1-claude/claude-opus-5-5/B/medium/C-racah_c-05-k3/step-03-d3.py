import numpy as np, itertools, functools
from sympy.physics.wigner import gaunt
ms=list(range(-2,3)); so=[(m,s) for m in ms for s in (0,1)]
idx={m:i for i,m in enumerate(ms)}
@functools.lru_cache(None)
def c(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*5*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
def apply(ops,D):
    st=list(D); sign=1
    for t,o in ops:
        if t=='a':
            if o not in st: return 0,None
            i=st.index(o); sign*=(-1)**i; st.pop(i)
        else:
            if o in st: return 0,None
            st.insert(0,o); k=0
            while k<len(st)-1 and st[k]>st[k+1]:
                st[k],st[k+1]=st[k+1],st[k]; sign*=-1; k+=1
    return sign,tuple(st)
dets=list(itertools.combinations(range(10),3)); di={d:i for i,d in enumerate(dets)}
N=len(dets)
H1=np.zeros((N,N)); H2={2:np.zeros((N,N)),4:np.zeros((N,N))}
h=np.zeros((5,5))
h[idx[0],idx[0]]=6; h[idx[1],idx[1]]=h[idx[-1],idx[-1]]=-4
h[idx[2],idx[2]]=h[idx[-2],idx[-2]]=1; h[idx[2],idx[-2]]=h[idx[-2],idx[2]]=5
for J,D in enumerate(dets):
    for p in range(10):
        for q in range(10):
            if so[p][1]!=so[q][1]: continue
            hv=h[idx[so[p][0]],idx[so[q][0]]]
            if hv==0: continue
            sg,st=apply([('a',q),('c',p)],D)
            if st: H1[di[st],J]+=sg*hv
    for r,s in itertools.permutations(D,2):
        for p,q in itertools.permutations(range(10),2):
            (mp,sp),(mq,sq),(mr,sr),(ms_,ss)=so[p],so[q],so[r],so[s]
            if sp!=sr or sq!=ss or mp+mq!=mr+ms_: continue
            sg,st=apply([('a',r),('a',s),('c',q),('c',p)],D)
            if not st: continue
            for k in (2,4):
                H2[k][di[st],J]+=0.5*sg*c(k,mp,mr)*c(k,ms_,mq)
np.save('H1.npy',H1); np.save('H2.npy',H2[2]); np.save('H4.npy',H2[4])
