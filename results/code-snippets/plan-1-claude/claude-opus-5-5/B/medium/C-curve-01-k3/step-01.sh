
cat << 'EOF' > /tmp/d4.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import sqrt as ssqrt
B=821.;C=3657.
F2=(B+C/7)*49;F4=(C/35)*441
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):  # c^k(l m1, l m2)
    return float(gaunt(2,k,2,-m1,m1-m2,m2)*(-1)**m1*ssqrt(4*np.pi/(2*k+1)))
Fk={0:0,2:F2,4:F4}
U={}
for a,b,c,d in itertools.product(ms,repeat=4):
    if a+b!=c+d: continue
    U[(a,b,c,d)]=sum(Fk[k]*ck(k,a,c)*ck(k,d,b) for k in (2,4))
# spin-orbitals (m,s)
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),4)); idx={d:i for i,d in enumerate(dets)}
N=len(dets)
# crystal field in m basis: Oh: V = Dq*(6 for eg...) ; matrix in complex basis
# real-basis: z2(m0), x2-y2=(m2+m-2)/sqrt2 eg; t2g others
h1=np.zeros((5,5))
def mi(m): return m+2
h1[mi(0),mi(0)]=6
h1[mi(1),mi(1)]=h1[mi(-1),mi(-1)]=-4
h1[mi(2),mi(2)]=h1[mi(-2),mi(-2)]=1
h1[mi(2),mi(-2)]=h1[mi(-2),mi(2)]=5
def apply_ops(det,ops):
    # ops list of (type,orb) applied right to left; returns sign,newdet
    st=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in st: return 0,None
            p=st.index(o);sign*=(-1)**p;st.pop(p)
        else:
            if o in st: return 0,None
            st.append(o);st.sort();p=st.index(o);sign*=(-1)**p
    return sign,tuple(st)
H1=np.zeros((N,N));H2=np.zeros((N,N))
for i,d in enumerate(dets):
    for p in range(10):
        for q in range(10):
            if so[p][1]!=so[q][1]: continue
            v=h1[mi(so[p][0]),mi(so[q][0])]
            if v==0: continue
            s,nd=apply_ops(d,[('c',p),('a',q)])
            if s: H1[idx[nd],i]+=s*v
    for p,q,r,t in itertools.product(range(10),repeat=4):
        if so[p][1]!=so[r][1] or so[q][1]!=so[t][1]: continue
        key=(so[p][0],so[q][0],so[r][0],so[so.index(so[t])][0])
        v=U.get(key,0)
        if v==0: continue
        s,nd=apply_ops(d,[('c',p),('c',q),('a',t),('a',r)])
        if s: H2[idx[nd],i]+=0.5*s*v
# S^2
Sz=np.diag([sum(0.5 if so[o][1]==0 else -0.5 for o in d) for d in dets])
Sp=np.zeros((N,N))
for i,d in enumerate(dets):
    for m in ms:
        p=so.index((m,0));q=so.index((m,1))
        s,nd=apply_ops(d,[('c',p),('a',q)])
        if s: Sp[idx[nd],i]+=s
S2=Sp.T@Sp+Sz@Sz+Sz
C4=np.diag([np.exp(1j*np.pi/2*sum(so[o][0] for o in d)) for d in dets])
def run(x):
    H=H2+x*B*H1
    w,v=np.linalg.eigh(H)
    groups=[];i=0
    while i<N:
        j=i
        while j<N and abs(w[j]-w[i])<1e-3: j+=1
        V=v[:,i:j];s2=np.real(np.trace(V.T@S2@V))/(j-i)
        S=(-1+np.sqrt(1+4*s2))/2;mult=int(round(2*S+1))
        ch=np.real(np.trace(V.conj().T@C4@V))/mult
        deg=(j-i)//mult
        lab={1:{1:'A1',-1:'A2'},2:{0:'E'},3:{1:'T1',-1:'T2'}}[deg].get(int(round(ch)),'?')
        groups.append((w[i],f"{mult}{lab}g"));i=j
    E0=groups[0][0]
    print(x,groups[0][1],[(g[1],round((g[0]-E0)/B,2)) for g in groups[1:4]])
for x in (0.9,2.15,3.35): run(x)
EOF
python3 /tmp/d4.py
