rm x; export MPLCONFIGDIR=/tmp/tsbench-run-fo0ckc8f/.mpl; cat > ts.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N
B=859.;C=3660.
F2=(B+C/7)*49; F4=(C/35)*441
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float(N((-1)**m1*gaunt(2,k,2,-m1,q,m2)))*np.sqrt(4*np.pi/(2*k+1))
CK={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
def U(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0.
    return F2*CK[(2,m1,m3)]*CK[(2,m4,m2)]+F4*CK[(4,m1,m3)]*CK[(4,m4,m2)]
so=[(m,s) for m in ms for s in (0.5,-0.5)]
n=7
dets=list(itertools.combinations(range(10),n))
idx={d:i for i,d in enumerate(dets)}
N_=len(dets)
H2=np.zeros((N_,N_))
def g(a,b,c,d):
    ma,sa=so[a];mb,sb=so[b];mc,sc=so[c];md,sd=so[d]
    v=0.
    if sa==sc and sb==sd: v+=U(ma,mb,mc,md)
    if sa==sd and sb==sc: v-=U(ma,mb,md,mc)
    return v
def apply_ann(det,o):
    if o not in det: return None
    i=det.index(o); return (-1)**i, tuple(x for x in det if x!=o)
def apply_cre(det,o):
    if o in det: return None
    l=sorted(det+(o,)); i=l.index(o); return (-1)**i, tuple(l)
pairs=[(a,b) for a in range(10) for b in range(a+1,10)]
for j,d in enumerate(dets):
    for (c,dd) in pairs:
        r=apply_ann(d,dd)
        if not r: continue
        s1,t=r; r=apply_ann(t,c)
        if not r: continue
        s2,t=r
        for (a,b) in pairs:
            r=apply_cre(t,b)
            if not r: continue
            s3,u=r; r=apply_cre(u,a)
            if not r: continue
            s4,u=r
            v=g(a,b,c,dd)
            if v: H2[idx[u],j]+=s1*s2*s3*s4*v
V=np.zeros((5,5))
for i,m in enumerate(ms): V[i,i]={0:6,1:-4,2:1}[abs(m)]
V[0,4]=V[4,0]=5
H1=np.zeros((N_,N_))
for j,d in enumerate(dets):
    for q in d:
        for p in range(10):
            if so[p][1]!=so[q][1]: continue
            v=V[ms.index(so[p][0]),ms.index(so[q][0])]
            if not v: continue
            r=apply_ann(d,q); s1,t=r; r=apply_cre(t,p)
            if not r: continue
            s2,u=r; H1[idx[u],j]+=s1*s2*v
print('herm',abs(H2-H2.T).max(),abs(H1-H1.T).max())
Sz=np.array([sum(so[o][1] for o in d) for d in dets])
S2=np.diag(Sz**2-Sz).astype(float)
for j,d in enumerate(dets):
    for q in d:
        if so[q][1]!=0.5: continue
        qd=so.index((so[q][0],-0.5))
        r=apply_ann(d,q); s1,t=r; r=apply_cre(t,qd)
        if not r: continue
        s2,u=r
        for q2 in u:
            if so[q2][1]!=-0.5: continue
            pu=so.index((so[q2][0],0.5))
            r=apply_ann(u,q2); s3,w=r; r=apply_cre(w,pu)
            if not r: continue
            s4,w=r; S2[idx[w],j]+=s1*s2*s3*s4
ML=np.array([sum(so[o][0] for o in d) for d in dets])
C4=np.exp(-1j*ML*np.pi/2)
labs={(1,1):'A1g',(1,-1):'A2g',(2,0):'Eg',(3,1):'T1g',(3,-1):'T2g'}
def levels(x,eps=1e-5):
    xx=max(x,eps)
    w,v=np.linalg.eigh(H2+xx*B*H1)
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and w[j]-w[i]<1e-8*B: j+=1
        vs=v[:,i:j]
        s2=np.trace(vs.T@S2@vs).real/(j-i); S=(-1+np.sqrt(1+4*s2))/2
        mult=int(round(2*S+1)); deg=(j-i)//mult
        ch=int(round((np.sum(np.abs(vs)**2*C4[:,None]).real)/mult))
        out.append([f"{mult}{labs[(deg,ch)]}",w[i]/B]); i=j
    g0=out[0][1]
    return [(l,e-g0) for l,e in out]
import json
xs=np.arange(0,4.01,0.5); res=[]
for x in xs:
    L=levels(x); res.append((float(x),[(l,float(e)) for l,e in L[:10]])); print(x,[(l,round(e,4)) for l,e in L[:8]])
json.dump(res,open('res.json','w'))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
xg=np.linspace(0,4,161); allE=[]
for x in xg:
    w=np.linalg.eigvalsh(H2+x*B*H1)/B; allE.append(w-w[0])
allE=np.array(allE)
plt.figure(figsize=(7,8)); plt.plot(xg,allE,'k-',lw=0.5)
plt.ylim(0,80); plt.xlabel('Dq/B'); plt.ylabel('E/B'); plt.title('d7 Oh Tanabe-Sugano, B=859, C=3660 cm-1')
plt.savefig('diagram.png',dpi=120)
EOF
python3 ts.py; sha256sum diagram.png