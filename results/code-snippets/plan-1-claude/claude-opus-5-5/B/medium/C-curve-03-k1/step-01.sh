cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=784.;C=3699.;F2=49*B+7*C;F4=441*C/35
F={0:0,2:F2,4:F4}
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):  # c^k(2m1,2m2)
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2)) if abs(m1-m2)<=k else 0.
# <m1 m2|1/r|m3 m4> = sum_k F^k c^k(m1,m3) c^k(m4,m2) delta(m1+m2,m3+m4)
U={}
for a,b,c,d in itertools.product(ms,repeat=4):
    if a+b!=c+d: continue
    U[(a,b,c,d)]=sum(F[k]*ck(k,a,c)*ck(k,d,b) for k in (2,4))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
def V1(Dq):
    v=np.zeros((5,5));
    for i,m in enumerate(ms): v[i,i]={2:Dq,-2:Dq,1:-4*Dq,-1:-4*Dq,0:6*Dq}[m]
    v[0,4]=v[4,0]=5*Dq; return v
def apply(ops,det):
    # ops list of (type,orb) applied right to left; returns sign,newdet
    st=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in st: return 0,None
            p=st.index(o);sign*=(-1)**p;st.pop(p)
        else:
            if o in st: return 0,None
            st.insert(0,o);
            # sort with sign
            p=sorted(st).index(o);sign*=(-1)**p;st=sorted(st)
    return sign,tuple(st)
N=len(dets)
H2=np.zeros((N,N));H1=np.zeros((N,N))
for j,d in enumerate(dets):
    for p in range(10):
        for q in range(10):
            if so[p][1]!=so[q][1]: continue
            s,nd=apply([('c',p),('a',q)],d)
            if s: H1[idx[nd],j]+=s*V1(1.0)[ms.index(so[p][0]),ms.index(so[q][0])]
    for p,q,r,t in itertools.product(range(10),repeat=4):
        if so[p][1]!=so[r][1] or so[q][1]!=so[t][1]: continue
        key=(so[p][0],so[q][0],so[r][0],so[t][0])
        if key not in U or U[key]==0: continue
        s,nd=apply([('c',p),('c',q),('a',t),('a',r)],d)
        if s: H2[idx[nd],j]+=0.5*s*U[key]
# S^2
S2=np.zeros((N,N))
for j,d in enumerate(dets):
    sz=sum(0.5 if so[o][1]==0 else -0.5 for o in d)
    S2[j,j]+=sz*sz+sz
    for p in range(10):
        for q in range(10):
            if so[p][0]==so[q][0] and so[p][1]==1 and so[q][1]==0: pass
    # S- S+ : S+ = sum c_up^dag c_dn
    for m in ms:
        up=so.index((m,0));dn=so.index((m,1))
        for m2 in ms:
            up2=so.index((m2,0));dn2=so.index((m2,1))
            s,nd=apply([('c',dn2),('a',up2),('c',up),('a',dn)],d)
            if s: S2[idx[nd],j]+=s
C4=np.diag([np.exp(-1j*np.pi/2*sum(so[o][0] for o in d)) for d in dets])
for x in (1.45,2.45,3.00):
    H=H2+x*B*H1
    w,v=np.linalg.eigh(H)
    w=np.round(w/B,5)
    levels=[];i=0
    while i<N:
        j=i
        while j<N and abs(w[j]-w[i])<1e-3: j+=1
        P=v[:,i:j];s2=np.real(np.trace(P.T@S2@P))/(j-i);S=(-1+np.sqrt(1+4*s2))/2
        mult=round(2*S+1);deg=(j-i)//mult;chi=np.real(np.trace(P.conj().T@C4@P))/mult
        lab={1:{1:'A1',-1:'A2'},2:{0:'E'},3:{1:'T1',-1:'T2'}}[deg].get(round(chi),'?')
        levels.append((w[i],f"{mult}{lab}"));i=j
    g=levels[0][0]
    print(x,[(l,round(e-g,3)) for e,l in levels[:5]])
EOF
python3 /tmp/d7.py