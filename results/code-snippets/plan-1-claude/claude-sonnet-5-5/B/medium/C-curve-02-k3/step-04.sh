cd /dev/shm && cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=1.0;C=3003/722
F4=63*C/5; F2=49*(B+5*F4/441); F={2:F2,4:F4}
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
ck={(k,a,b):c(k,a,b) for k in (2,4) for a in range(-2,3) for b in range(-2,3)}
orb=[(m,s) for m in range(-2,3) for s in (1,-1)]
def g(a,b,cc,d):
    if a[1]!=cc[1] or b[1]!=d[1] or a[0]+b[0]!=cc[0]+d[0]: return 0
    return sum(F[k]*ck[(k,a[0],cc[0])]*ck[(k,d[0],b[0])] for k in (2,4))
def apply(ops,t):
    st=list(t);sign=1
    for cr,o in reversed(ops):
        if cr:
            if o in st: return None
            pos=sum(1 for x in st if x<o); st.insert(pos,o); sign*=(-1)**pos
        else:
            if o not in st: return None
            pos=st.index(o); st.pop(pos); sign*=(-1)**pos
    return tuple(st),sign
def run(Dq):
    h=np.zeros((10,10))
    d={0:6,1:-4,-1:-4,2:1,-2:1}
    for i,(m,s) in enumerate(orb):
        h[i,i]=d[m]*Dq
        for j,(m2,s2) in enumerate(orb):
            if s==s2 and abs(m)==2 and m2==-m: h[i,j]=5*Dq
    dets=[t for t in itertools.combinations(range(10),3) if sum(orb[i][1] for i in t)==1]
    idx={t:i for i,t in enumerate(dets)}
    n=len(dets);H=np.zeros((n,n));Cm=np.zeros((n,n),complex)
    for t in dets:
        a=idx[t]
        for i in range(10):
            for j in range(10):
                if h[i,j]!=0:
                    r=apply([(1,i),(0,j)],t)
                    if r and r[0] in idx: H[idx[r[0]],a]+=h[i,j]*r[1]
        for i in range(10):
         for j in range(10):
          for k in range(10):
           for l in range(10):
            v=g(orb[i],orb[j],orb[k],orb[l])
            if v==0: continue
            r=apply([(1,i),(1,j),(0,l),(0,k)],t)
            if r and r[0] in idx: H[idx[r[0]],a]+=0.5*v*r[1]
        Cm[a,a]=np.exp(-1j*np.pi/2*sum(orb[i][0] for i in t))
    dets3=[t for t in itertools.combinations(range(10),3) if sum(orb[i][1] for i in t)==3]
    i3={t:i for i,t in enumerate(dets3)}
    Sp=np.zeros((len(dets3),n))
    for t in dets:
        for m in range(-2,3):
            r=apply([(1,orb.index((m,1))),(0,orb.index((m,-1)))],t)
            if r and r[0] in i3: Sp[i3[r[0]],idx[t]]+=r[1]
    S2=Sp.T@Sp+0.75*np.eye(n)
    H=(H+H.T)/2
    w,v=np.linalg.eigh(H)
    out=[];i=0
    while i<n:
        j=i
        while j+1<n and abs(w[j+1]-w[i])<1e-6: j+=1
        V=v[:,i:j+1]
        s2=np.trace(V.T@S2@V).real/(j-i+1); tr=np.trace(V.conj().T@Cm@V).real
        out.append((w[i],j-i+1,round(s2,2),round(tr,2)));i=j+1
    return out
for Dq in (1.0,2.2,3.5):
    o=run(Dq);g0=o[0][0]
    print(Dq,[(round(e-g0,3),d,s,t) for e,d,s,t in o[:8]])
E
python3 a.py