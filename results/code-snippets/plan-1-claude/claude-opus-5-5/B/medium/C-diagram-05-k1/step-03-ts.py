import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=859.;C=3660.;l=2
F4=C/35;F2=B+5*F4
Fk={0:0.0,2:49*F2,4:441*F4}
def ck(k,m,mp):
    return float((-1)**m*(2*l+1)*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m,m-mp,mp))
ms=range(-2,3)
so=[(m,s) for m in ms for s in (1,-1)]
def U(a,b,c,d): # <ab|1/r|cd>, electron1 a->c, 2 b->d
    if so[a][1]!=so[c][1] or so[b][1]!=so[d][1]: return 0.
    m1,m2,m3,m4=so[a][0],so[b][0],so[c][0],so[d][0]
    if m1+m2!=m3+m4: return 0.
    return sum(ck(k,m1,m3)*ck(k,m4,m2)*Fk[k] for k in (0,2,4))
N=10
Ut=np.zeros((N,)*4)
for a,b,c,d in itertools.product(range(N),repeat=4): Ut[a,b,c,d]=U(a,b,c,d)
def V1(Dq):
    v=np.zeros((N,N))
    diag={0:6,1:-4,-1:-4,2:1,-2:1}
    for i,(m,s) in enumerate(so):
        for j,(mp,sp) in enumerate(so):
            if s!=sp: continue
            if m==mp: v[i,j]=diag[m]*Dq
            if abs(m-mp)==4: v[i,j]=5*Dq
    return v
dets=list(itertools.combinations(range(N),7))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(det,ops):
    # ops list of (orb, create?) applied right-to-left; returns sign,newdet or None
    st=list(det);sign=1
    for o,cr in reversed(ops):
        if cr:
            if o in st: return None
            pos=sum(1 for x in st if x<o); sign*=(-1)**pos; st.insert(pos,o)
        else:
            if o not in st: return None
            pos=st.index(o); sign*=(-1)**pos; st.pop(pos)
    return sign,tuple(st)
D=len(dets)
H2=np.zeros((D,D))
for j,d in enumerate(dets):
    for a,b in itertools.combinations(d,2):
        for c in range(N):
            for e in range(N):
                u=Ut[c,e,a,b]
                if u==0: continue
                r=apply_ops(d,[(c,1),(e,1),(b,0),(a,0)])
                if r: H2[idx[r[1]],j]+=0.5*u*r[0]
                # pair (b,a) ordering also counted:
                u2=Ut[c,e,b,a]
                if u2:
                    r=apply_ops(d,[(c,1),(e,1),(a,0),(b,0)])
                    if r: H2[idx[r[1]],j]+=0.5*u2*r[0]
def onebody(v):
    M=np.zeros((D,D))
    for j,d in enumerate(dets):
        for a in d:
            for c in range(N):
                if v[c,a]==0: continue
                r=apply_ops(d,[(c,1),(a,0)])
                if r: M[idx[r[1]],j]+=v[c,a]*r[0]
    return M
HV=onebody(V1(1.0))
ML=np.array([sum(so[o][0] for o in d) for d in dets])
MS=np.array([sum(so[o][1] for o in d) for d in dets])/2
# S^2
Sp=np.zeros((N,N))
for i,(m,s) in enumerate(so):
    if s==-1: Sp[so.index((m,1)),i]=1
SpM=onebody(Sp); S2=SpM.T@SpM+np.diag(MS**2-MS)  # S-S+ = S^2 - Sz^2 - Sz -> S^2=S-S+ + Sz^2+Sz
S2=SpM.T@SpM+np.diag(MS**2+MS)
assert np.allclose(H2,H2.T)
def levels(Dq):
    H=H2+Dq*B*HV
    out=[]
    for Smax in (1.5,0.5):
        sel=np.where(np.isclose(MS,Smax))[0]
        w,v=np.linalg.eigh(H[np.ix_(sel,sel)])
        ph=np.exp(1j*np.pi/2*ML[sel])
        i=0
        while i<len(w):
            j=i
            while j<len(w) and abs(w[j]-w[i])<1e-6*B: j+=1
            vv=v[:,i:j]
            s2=np.trace(vv.T@S2[np.ix_(sel,sel)]@vv).real/(j-i)
            S=(-1+np.sqrt(1+4*s2))/2
            if abs(S-Smax)<1e-3:
                chi=np.trace(vv.conj().T@(ph[:,None]*vv)).real
                dim=j-i
                lab={1:{1:'A1g',-1:'A2g'},2:{0:'Eg'},3:{1:'T1g',-1:'T2g'}}[dim][int(round(chi))]
                out.append((w[i],int(2*Smax+1),lab))
            i=j
    out.sort()
    return out
