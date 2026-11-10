import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
def gnt(k,a,b,q):
    if abs(a)>2 or abs(b)>2 or abs(q)>k: return 0.0
    return float(gaunt(2,2,k,a,b,q).evalf())
def Ak(k,m1,m2,m3,m4):
    tot=0.0
    for q in range(-k,k+1):
        if -m1+m3-q!=0 or -m2+m4+q!=0: continue
        tot+=((-1)**(m1+q))*gnt(k,-m1,m3,-q)*((-1)**m2)*gnt(k,-m2,m4,q)
    return 4*np.pi/(2*k+1)*tot
Vt={}
for k in (0,2,4):
    arr=np.zeros((5,5,5,5))
    for i,m1 in enumerate(ms):
        for j,m2 in enumerate(ms):
            for a,m3 in enumerate(ms):
                for b,m4 in enumerate(ms):
                    if m1+m2==m3+m4: arr[i,j,a,b]=Ak(k,m1,m2,m3,m4)
    Vt[k]=arr
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[ms.index(m)]=c
    return v
s2=np.sqrt(2)
t2g=[vec({2:1/(1j*s2),-2:-1/(1j*s2)}), vec({1:1/(1j*s2),-1:1/(1j*s2)}), vec({1:1/s2,-1:-1/s2})]
eg=[vec({2:1/s2,-2:1/s2}), vec({0:1.0})]
def hcf(Dq):
    h=np.zeros((5,5),complex)
    for v in t2g: h+=-4*Dq*np.outer(v,v.conj())
    for v in eg: h+=6*Dq*np.outer(v,v.conj())
    return h
dets=list(itertools.combinations(range(5),3))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(state, ops):
    st=list(state); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in st: return None,0
            p=st.index(i); sign*=(-1)**p; st.pop(p)
        else:
            if i in st: return None,0
            p=sum(1 for x in st if x<i); sign*=(-1)**p; st.insert(p,i)
    return tuple(st),sign
def H_full(Dq,F):
    n=len(dets); h1=hcf(Dq)
    Vm=sum(F[k]*Vt[k] for k in (0,2,4))
    H=np.zeros((n,n),complex)
    for d in dets:
        j=idx[d]
        for a in range(5):
            for b in range(5):
                if abs(h1[a,b])<1e-14: continue
                st,sg=apply_ops(d,[('c',a),('a',b)])
                if st is not None: H[idx[st],j]+=h1[a,b]*sg
        for a in range(5):
            for b in range(5):
                for c in range(5):
                    for e in range(5):
                        val=Vm[a,b,c,e]
                        if abs(val)<1e-14: continue
                        st,sg=apply_ops(d,[('c',a),('c',b),('a',e),('a',c)])
                        if st is not None: H[idx[st],j]+=0.5*val*sg
    return H
def levels(Dq,F):
    H=H_full(Dq,F)
    return np.linalg.eigvalsh((H+H.conj().T)/2)
r=40.5/57.5
def Fs(B):
    F2=441*B/(9-5*r); return {0:0.0,2:F2,4:r*F2}
def quartet(Dq,B):
    w=np.sort(levels(Dq,Fs(B)))
    vals=[];mult=[]
    for x in w:
        if vals and abs(x-vals[-1])<1e-6: mult[-1]+=1
        else: vals.append(x); mult.append(1)
    return vals,mult
