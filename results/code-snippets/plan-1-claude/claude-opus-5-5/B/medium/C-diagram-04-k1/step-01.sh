mkdir -p /tmp/w && cd /tmp/w && cat > ts.py <<'EOF'
import numpy as np, itertools, hashlib
from sympy.physics.wigner import gaunt
B=551.;C=2511.
F2=B+C/7;F4=C/35;Fk={0:0.,2:49*F2,4:441*F4}
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) <m1|Y_k,m1-m2|m2>
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*25/5*gaunt(2,k,2,-m1,q,m2)) if False else float((-1)**m1*5*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def g(a,b,c,d): # <ab|1/r|cd>, orbitals m
    if a+b!=c+d: return 0.
    return sum(CK[(k,a,c)]*CK[(k,d,b)]*Fk[k] for k in (2,4))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),6)); idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def two(i,j,k,l):
    (a,sa),(b,sb),(c,sc),(d,sd)=so[i],so[j],so[k],so[l]
    v=0.
    if sa==sc and sb==sd: v+=g(a,b,c,d)
    if sa==sd and sb==sc: v-=g(a,b,d,c)
    return v
# build via second quantization: H2 = 1/2 sum <ij||kl> a+i a+j a_l a_k
def apply_ann(det,p):
    if p not in det: return None,0
    k=det.index(p); return tuple(x for x in det if x!=p),(-1)**k
def apply_cre(det,p):
    if p in det: return None,0
    k=sum(1 for x in det if x<p); return tuple(sorted(det+(p,))),(-1)**k
def op_matrix(oneb,twob):
    H=np.zeros((N,N),complex)
    for d in dets:
        for (i,k),v in oneb.items():
            d1,s1=apply_ann(d,k)
            if d1 is None: continue
            d2,s2=apply_cre(d1,i)
            if d2 is None: continue
            H[idx[d2],idx[d]]+=v*s1*s2
        for (i,j,k,l),v in twob.items():
            d1,s1=apply_ann(d,k);
            if d1 is None: continue
            d2,s2=apply_ann(d1,l)
            if d2 is None: continue
            d3,s3=apply_cre(d2,j)
            if d3 is None: continue
            d4,s4=apply_cre(d3,i)
            if d4 is None: continue
            H[idx[d4],idx[d]]+=0.5*v*s1*s2*s3*s4
    return H
tb={}
for i,j,k,l in itertools.product(range(10),repeat=4):
    v=two(i,j,k,l)
    if abs(v)>1e-12: tb[(i,j,k,l)]=v
Hee=op_matrix({},tb)
cf={(0,2):1.,(1,1):-4.,(2,0):6.,(3,-1):-4.,(4,-2):1.,(-2,2):5.,(2,-2):5.}  # m-index of ms
ob={}
for i in range(10):
    for k in range(10):
        (a,sa),(c,sc)=so[i],so[k]
        if sa!=sc: continue
        ia,ic=ms.index(a),ms.index(c)
        if a==c: v={-2:1,-1:-4,0:6,1:-4,2:1}[a]
        elif {a,c}=={2,-2}: v=5
        else: continue
        ob[(i,k)]=v
Hcf=op_matrix(ob,{})
# S^2
ob2={};
Sz=np.diag([sum(0.5 if so[p][1]==0 else -0.5 for p in d) for d in dets])
spl={}
for m in ms: spl[(so.index((m,0)),so.index((m,1)))]=1.
Sp=op_matrix(spl,{})
S2=Sp.conj().T@Sp+Sz@Sz+Sz
# C4 orbital: |m> -> exp(-i m pi/2)|m>
R=np.diag([np.prod([np.exp(-1j*so[p][0]*np.pi/2) for p in d]) for d in dets])
# C3 about (111) harder; use C4 + C2' ? characters C4: A1 1,A2 -1,E 0,T1 1,T2 -1 ; dims distinguish
lab={(1,1):'A1g',(1,-1):'A2g',(2,0):'Eg',(3,1):'T1g',(3,-1):'T2g'}
print(np.allclose(Hee,Hee.conj().T),np.allclose(Hcf,Hcf.conj().T))
res=[];curves=[]
grid=np.arange(0,4.01,0.5); fine=np.linspace(0,4,161)
def levels(x):
    dq=max(x,1e-5)*B
    H=Hee+dq*Hcf
    w,v=np.linalg.eigh(H)
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and w[j]-w[i]<1e-6*B: j+=1
        V=v[:,i:j]; n=j-i
        s2=np.real(np.trace(V.conj().T@S2@V))/n; S=(-1+np.sqrt(1+4*s2))/2; mult=int(round(2*S+1))
        dim=n//mult; chi=np.real(np.trace(V.conj().T@R@V))/mult
        key=(dim,int(round(chi)))
        out.append((w[i],f"{mult}{lab.get(key,str(key))}",n)); i=j
    return out
for x in grid:
    L=levels(x); e0=L[0][0]
    pts=[(t,round((e-e0)/B,3)) for e,t,n in L[:6]]
    print(x,pts); res.append(pts)
import json; json.dump([[float(x),r] for x,r in zip(grid,res)],open('res.json','w'))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
E=[];
for x in fine:
    L=levels(x); e0=L[0][0]; E.append([(e-e0)/B for e,t,n in L[:40]])
E=np.array([e[:min(map(len,E))] for e in E])
plt.figure(figsize=(7,8)); plt.plot(fine*10,E,'k',lw=.7); plt.xlabel('Δo/B'); plt.ylabel('E/B'); plt.ylim(0,80); plt.title('d6 Oh, C/B=%.3f'%(C/B))
plt.savefig('/tmp/w/diagram.png',dpi=120)
EOF
python ts.py