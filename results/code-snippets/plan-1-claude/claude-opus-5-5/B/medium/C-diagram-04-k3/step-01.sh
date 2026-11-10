mkdir -p /tmp/w && cd /tmp/w && cat > ts.py <<'EOF'
import numpy as np, itertools, hashlib
from sympy.physics.wigner import gaunt
from sympy import N
B,C=551.,2511.
F4=C/35/B; F2=1+5*C/35/B   # units of B
Fk={2:49*F2,4:441*F4}
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # c^k(l m1, l m2)
    return float(N((-1)**m1*np.sqrt(5*5)*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2)))
c={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
def V2(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0.
    return sum(c[(k,m1,m3)]*c[(k,m4,m2)]*Fk[k] for k in (2,4))
so=[(m,s) for m in ms for s in (1,-1)]  # 10 spin orbitals
dets=list(itertools.combinations(range(10),6)); idx={d:i for i,d in enumerate(dets)}
n=len(dets)
def apply2(det,p,q,r,s_):  # a+_p a+_q a_s a_r |det>
    d=list(det); sign=1
    for o in (r,s_):
        if o not in d: return None,0
    # annihilate s then r
    for o in (s_,r):
        i=d.index(o); sign*=(-1)**i; d.pop(i)
    for o in (q,p):
        if o in d: return None,0
        d.insert(0,o); 
    # sort with sign
    arr=d[:]; 
    for i in range(len(arr)):
        for j in range(len(arr)-1-i):
            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sign=-sign
    return tuple(arr),sign
H=np.zeros((n,n))
# Coulomb: 1/2 sum V(pq,rs) a+p a+q a s a r
for d in dets:
    i=idx[d]
    for r in d:
        for s_ in d:
            if r==s_: continue
            for p in range(10):
                for q in range(10):
                    if p==q: continue
                    if so[p][1]!=so[r][1] or so[q][1]!=so[s_][1]: continue
                    v=V2(so[p][0],so[q][0],so[r][0],so[s_][0])
                    if abs(v)<1e-12: continue
                    nd,sg=apply2(d,p,q,r,s_)
                    if nd is None: continue
                    H[idx[nd],i]+=0.5*v*sg
# crystal field one-body (per Dq)
cf1=np.zeros((10,10))
diag={0:6,1:-4,-1:-4,2:1,-2:1}
for a,(m,s) in enumerate(so):
    for b,(m2,s2) in enumerate(so):
        if s!=s2: continue
        if m==m2: cf1[a,b]=diag[m]
        elif abs(m-m2)==4: cf1[a,b]=5
def onebody(h):
    M=np.zeros((n,n))
    for d in dets:
        i=idx[d]
        for b in d:
            for a in range(10):
                if abs(h[a,b])<1e-14: continue
                dl=list(d); k=dl.index(b); sg=(-1)**k; dl.pop(k)
                if a in dl: continue
                dl.insert(0,a); arr=dl
                for x in range(len(arr)):
                    for y in range(len(arr)-1-x):
                        if arr[y]>arr[y+1]: arr[y],arr[y+1]=arr[y+1],arr[y]; sg=-sg
                M[idx[tuple(arr)],i]+=h[a,b]*sg
    return M
CF=onebody(cf1)
# S^2
sp=np.zeros((10,10))
for a,(m,s) in enumerate(so):
    for b,(m2,s2) in enumerate(so):
        if m==m2 and s==1 and s2==-1: sp[a,b]=1
Sp=onebody(sp); Sz=np.diag([sum(so[o][1] for o in d)/2 for d in dets])
S2=Sp.T@Sp+Sz@Sz+Sz
ML=np.array([sum(so[o][0] for o in d) for d in dets])
rot=np.exp(-1j*np.pi/2*ML)
assert np.allclose(H,H.T)
lab={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}
def levels(dq):
    w,v=np.linalg.eigh(H+max(dq,1e-5)*CF)
    w0=np.linalg.eigvalsh(H+dq*CF)
    out=[];i=0
    while i<n:
        j=i
        while j<n and w[j]-w[i]<1e-7: j+=1
        V=v[:,i:j]; s2=np.trace(V.T@S2@V)/(j-i); S=(-1+np.sqrt(1+4*s2))/2
        mult=int(round(2*S+1)); dim=(j-i)//mult
        chi=np.real(np.sum(np.abs(V)**2*rot[:,None]))/mult
        out.append((w0[i],f"{mult}{lab[(dim,int(round(chi)))]}g")); i=j
    return out
import json
res=[];allL={}
for dq in np.arange(0,4.01,0.5):
    L=levels(dq); e0=L[0][0]
    res.append({"dq_over_b":float(dq),"levels":[{"term":t,"e_over_b":round(float(e-e0),3)} for e,t in L[:6]]})
    print(dq,[(t,round(e-e0,3)) for e,t in L[:8]])
json.dump(res,open('res.json','w'))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
xs=np.linspace(0,4,161); Ys=[]
for x in xs:
    w=np.unique(np.round(np.linalg.eigvalsh(H+x*CF),6)); Ys.append(w-w[0])
plt.figure(figsize=(7,8))
for x,y in zip(xs,Ys): plt.plot([x]*len(y),y,'k.',ms=1)
plt.ylim(0,80);plt.xlabel('Dq/B');plt.ylabel('E/B');plt.title('d6 Oh, B=551, C=2511 cm-1')
plt.savefig('diagram.png',dpi=120)
EOF
python ts.py && cp diagram.png $OLDPWD/ 2>/dev/null; cd - && sha256sum diagram.png && realpath diagram.png