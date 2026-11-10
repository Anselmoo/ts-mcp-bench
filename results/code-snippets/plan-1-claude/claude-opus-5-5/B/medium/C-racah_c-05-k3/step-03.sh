
mkdir -p $TMPDIR; cd $TMPDIR
cat << 'EOF' > d3.py
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
EOF
python3 d3.py && cat << 'EOF' > fit.py
import numpy as np
from scipy.optimize import least_squares
H1=np.load('H1.npy');H2=np.load('H2.npy');H4=np.load('H4.npy')
def lev(Dq,B,C):
    F2=49*B+7*C; F4=63*C
    # F2 = F^2/49 etc: Racah B=F2-5F4, C=35F4 with F2=F^2/49,F4=F^4/441
    H=Dq*H1+F2*49*H2/49+0
    H=Dq*H1+(49*B+7*C)*H2+ (441*C/35)*H4
    w=np.linalg.eigvalsh(H); return w-w[0]
def uniq(w):
    out=[];cnt=[]
    for x in w:
        if out and abs(x-out[-1])<1e-3: cnt[-1]+=1
        else: out.append(x);cnt.append(1)
    return list(zip(np.round(out,1),cnt))
print(uniq(lev(1750,618,2472))[:8])
def res(p):
    Dq,B,C=p; u=uniq(lev(Dq,B,C))
    # degeneracies: 4A2(4),2E(4),2T1(6),4T2(12)...
    e={}
    for x,n in u: e.setdefault(n,[]).append(x)
    return u
EOF
python3 fit.py
