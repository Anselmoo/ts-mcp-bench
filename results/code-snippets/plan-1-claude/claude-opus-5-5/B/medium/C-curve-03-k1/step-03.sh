python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=784.;C=3699.;F2=49*B+7*C;F4=441*C/35
F={0:0,2:F2,4:F4}
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2)) if abs(m1-m2)<=k else 0.
U={}
for a,b,c,d in itertools.product(ms,repeat=4):
    if a+b!=c+d: continue
    U[(a,b,c,d)]=sum(F[k]*ck(k,a,c)*ck(k,d,b) for k in (2,4))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
v=np.zeros((5,5))
for i,m in enumerate(ms): v[i,i]={2:1,-2:1,1:-4,-1:-4,0:6}[m]
v[0,4]=v[4,0]=5
def apply(ops,det):
    st=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in st: return 0,None
            p=st.index(o);sign*=(-1)**p;st.pop(p)
        else:
            if o in st: return 0,None
            st.append(o);st=sorted(st);p=st.index(o);sign*=(-1)**p
    return sign,tuple(st)
N=len(dets)
H2=np.zeros((N,N));H1=np.zeros((N,N));S2=np.zeros((N,N))
for j,d in enumerate(dets):
    for p in range(10):
        for q in range(10):
            if so[p][1]!=so[q][1]: continue
            s,nd=apply([('c',p),('a',q)],d)
            if s: H1[idx[nd],j]+=s*v[ms.index(so[p][0]),ms.index(so[q][0])]
    for p,q,r,t in itertools.product(range(10),repeat=4):
        if so[p][1]!=so[r][1] or so[q][1]!=so[t][1]: continue
        key=(so[p][0],so[q][0],so[r][0],so[t][0])
        if abs(U.get(key,0))<1e-12: continue
        s,nd=apply([('c',p),('c',q),('a',t),('a',r)],d)
        if s: H2[idx[nd],j]+=0.5*s*U[key]
    sz=sum(0.5 if so[o][1]==0 else -0.5 for o in d)
    S2[j,j]+=sz*sz-sz
    for m in ms:
        for m2 in ms:
            s,nd=apply([('c',so.index((m2,0))),('a',so.index((m2,1))),('c',so.index((m,1))),('a',so.index((m,0)))],d)
            if s: S2[idx[nd],j]+=s
print(np.abs(H2-H2.T).max(),np.abs(H1-H1.T).max())
C4=np.diag([np.exp(-1j*np.pi/2*sum(so[o][0] for o in d)) for d in dets])
for x in (0,1.45,2.45,3.00):
    H=H2+x*B*H1
    w,vv=np.linalg.eigh(H); w=w/B
    levels=[];i=0
    while i<N:
        j=i
        while j<N and abs(w[j]-w[i])<1e-6: j+=1
        P=vv[:,i:j];s2=np.trace(P.T@S2@P)/(j-i);S=(-1+np.sqrt(1+4*s2))/2
        mult=round(2*S+1);deg=(j-i)//mult;chi=np.real(np.trace(P.conj().T@C4@P))/mult
        lab={1:{1:'A1',-1:'A2'},2:{0:'E'},3:{1:'T1',-1:'T2'}}.get(deg,{}).get(round(chi),'?%d'%deg)
        levels.append((w[i],f"{mult}{lab}"));i=j
    g=levels[0][0]
    print(x,[(l,round(e-g,3)) for e,l in levels[:6]])
EOF