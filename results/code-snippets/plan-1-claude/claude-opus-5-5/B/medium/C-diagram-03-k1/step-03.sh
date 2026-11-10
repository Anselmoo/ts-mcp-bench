mkdir -p /tmp/w && cd /tmp/w && cat > ts.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=806.;C=3570.
F2=49*B+7*C; F4=441*C/35
ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
U=np.zeros((5,5,5,5))
for a,b,c,d in itertools.product(range(5),repeat=4):
    m1,m2,m3,m4=ms[a],ms[b],ms[c],ms[d]
    if m1+m2!=m3+m4: continue
    U[a,b,c,d]=sum(Fk*ck(k,m1,m3)*ck(k,m4,m2) for k,Fk in ((2,F2),(4,F4)))
# spin orbitals: index = 2*orb+spin
n=10
def orb(i): return i//2
def sp(i): return i%2
dets=[s for s in itertools.combinations(range(n),5) if sum(1 if sp(i)==0 else -1 for i in s)==1]
idx={d:k for k,d in enumerate(dets)}
N=len(dets)
def apply_ann(det,i):
    if i not in det: return None,0
    p=det.index(i); return tuple(x for x in det if x!=i),(-1)**p
def apply_cre(det,i):
    if i in det: return None,0
    l=sorted(det+(i,)); p=l.index(i); return tuple(l),(-1)**p
def op1(det,i,j):
    d,s1=apply_ann(det,j)
    if d is None: return None,0
    d,s2=apply_cre(d,i)
    if d is None: return None,0
    return d,s1*s2
Hc=np.zeros((N,N));V=np.zeros((N,N),complex);S2=np.zeros((N,N))
Vorb=np.zeros((5,5)); 
for k,m in enumerate(ms): Vorb[k,k]={0:6,1:-4,2:1}[abs(m)]
Vorb[0,4]=Vorb[4,0]=5
for col,det in enumerate(dets):
    # one body V
    for i in range(n):
        for j in range(n):
            if sp(i)!=sp(j) or Vorb[orb(i),orb(j)]==0: continue
            d,s=op1(det,i,j)
            if d is None: continue
            V[idx[d],col]+=s*Vorb[orb(i),orb(j)]
    # two body: 1/2 sum <ij|kl> a+i a+j a_l a_k
    for k in det:
        for l in det:
            if k==l: continue
            d,s1=apply_ann(det,k); d,s2=apply_ann(d,l)
            for i in range(n):
                for j in range(n):
                    if sp(i)!=sp(k) or sp(j)!=sp(l): continue
                    u=U[orb(i),orb(j),orb(k),orb(l)]
                    if u==0: continue
                    e,s3=apply_cre(d,j)
                    if e is None: continue
                    e,s4=apply_cre(e,i)
                    if e is None: continue
                    Hc[idx[e],col]+=0.5*u*s1*s2*s3*s4
    # S^2 = S-S+ + Sz^2 + Sz, Sz=1/2
    tmp={}
    for i in range(n):
        if sp(i)!=1: continue
        d,s=op1(det,i-1,i)  # S+ : down->up
        if d is None: continue
        for j in range(n):
            if sp(j)!=0: continue
            e,t=op1(d,j+1,j)
            if e is None: continue
            S2[idx[e],col]+=s*t
    S2[col,col]+=0.75
V=V.real
# C4 phases
c4=np.array([np.exp(1j*np.pi/2*sum(ms[orb(i)] for i in d)) for d in dets])
labels={}
def classify(Dq):
    H=Hc+Dq*B*V+1e-3*S2 + (1e-4*V if Dq==0 else 0)
    w,v=np.linalg.eigh(H)
    out=[];k=0
    while k<N:
        g=[k]
        while k+len(g)<N and abs(w[k+len(g)]-w[k])<1e-6: g.append(k+len(g))
        vv=v[:,g]
        s2=np.real(np.trace(vv.T@S2@vv))/len(g)
        S=(-1+np.sqrt(1+4*s2))/2; mult=int(round(2*S+1))
        chi=np.real(np.trace(vv.conj().T@(c4[:,None]*vv)))
        dim=len(g)
        lab={(1,1):'A1g',(1,-1):'A2g',(2,0):'E g',(3,1):'T1g',(3,-1):'T2g'}.get((dim,int(round(chi))),f'?{dim},{chi:.2f}')
        lab=lab.replace(' ','')
        E=(w[k]-1e-3*s2)/B
        out.append((E,f'{mult}{lab}'))
        k+=len(g)
    E0=out[0][0]
    return [(e-E0,l) for e,l in out]
import json
res=[]
for dq in np.arange(0,4.01,0.5):
    r=classify(dq); res.append((dq,r))
    print(dq,[(l,round(e,3)) for e,l in r[:9]])
json.dump([(dq,[(l,e) for e,l in r]) for dq,r in res],open('res.json','w'))
# plot
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
xs=np.linspace(0,4,161); data=[classify(x) for x in xs]
import collections
pts=collections.defaultdict(list)
for x,r in zip(xs,data):
    for e,l in r:
        if e<80: pts[l].append((x,e))
plt.figure(figsize=(8,8))
for l,p in pts.items():
    p=np.array(p); plt.plot(p[:,0],p[:,1],'.',ms=1.5,label=l)
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.title('d5 Oh, C/B=%.3f'%(C/B));plt.ylim(0,80)
plt.legend(fontsize=6,markerscale=5,ncol=2);plt.savefig('diagram.png',dpi=120)
EOF
MPLCONFIGDIR=/tmp/w python3 ts.py