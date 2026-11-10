import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=828.;C=3390.
l=2
def ck(k,m,mp):
    return float((-1)**m*(2*l+1)*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m,m-mp,mp))
F={2:49*B+7*C,4:441*C/35}
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
N=10
Vt=np.zeros((N,)*4)
for a,b,c,d in itertools.product(range(N),repeat=4):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[a],so[b],so[c],so[d]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: continue
    Vt[a,b,c,d]=sum(ck(k,m1,m3)*ck(k,m4,m2)*F[k] for k in (2,4))
dets=list(itertools.combinations(range(N),3)); idx={d:i for i,d in enumerate(dets)}
nd=len(dets)
def ann(o,st):
    if o not in st: return 0,None
    i=st.index(o); return (-1)**i, st[:i]+st[i+1:]
def cre(o,st):
    if o in st: return 0,None
    i=sum(1 for x in st if x<o); return (-1)**i, tuple(sorted(st+(o,)))
def ops(seq,st):  # seq applied right-to-left: list of ('c'/'a',o) leftmost first
    sg=1
    for t,o in reversed(seq):
        s,st=(cre if t=='c' else ann)(o,st)
        if s==0: return 0,None
        sg*=s
    return sg,st
H2=np.zeros((nd,nd))
nz=np.argwhere(Vt!=0)
for j,det in enumerate(dets):
    for p,q,r,s in nz:
        sg,st=ops([('c',p),('c',q),('a',s),('a',r)],det)
        if sg: H2[idx[st],j]+=0.5*Vt[p,q,r,s]*sg
# CF one-electron in m basis (units Dq)
cf=np.zeros((5,5)); mi={m:i for i,m in enumerate(ms)}
cf[mi[0],mi[0]]=6; cf[mi[1],mi[1]]=cf[mi[-1],mi[-1]]=-4
cf[mi[2],mi[2]]=cf[mi[-2],mi[-2]]=1; cf[mi[2],mi[-2]]=cf[mi[-2],mi[2]]=5
H1=np.zeros((nd,nd))
for j,det in enumerate(dets):
    for a in range(N):
        for b in range(N):
            if so[a][1]!=so[b][1]: continue
            v=cf[mi[so[a][0]],mi[so[b][0]]]
            if v==0: continue
            sg,st=ops([('c',a),('a',b)],det)
            if sg: H1[idx[st],j]+=v*sg
# S^2
S2=np.zeros((nd,nd))
def sz(det): return sum(0.5 if so[o][1]==0 else -0.5 for o in det)
for j,det in enumerate(dets):
    S2[j,j]+=sz(det)**2
    # S-S+ ; S^2 = S-S+ + Sz^2 + Sz
    S2[j,j]+=sz(det)
    for a in range(0,N,2):
        for b in range(0,N,2):
            if so[a][0]!=so[b][0]:continue
            # S- S+ = sum c+_{b dn} c_{b up} c+_{a up} c_{a dn}
            sg,st=ops([('c',b+1),('a',b),('c',a),('a',a+1)],det)
            if sg: S2[idx[st],j]+=sg
# C4 (orbital only): phase exp(i m pi/2) -> diagonal on dets ; C3 about (111) harder; use C4 and C2' maybe. Use C4 plus degeneracy.
C4=np.array([np.prod([1j**so[o][0] for o in det]) for det in dets])
def levels(dq,tol=1e-6):
    H=H2+dq*B*H1
    w,v=np.linalg.eigh(H)
    out=[];i=0
    while i<nd:
        j=i
        while j<nd and abs(w[j]-w[i])<1e-5*B: j+=1
        P=v[:,i:j]
        s2=np.trace(P.T@S2@P).real/(j-i)
        S=round((-1+np.sqrt(1+4*s2))/2*2)/2
        mult=int(round(2*S+1)); dim=(j-i)//mult
        chi=(np.einsum('ik,i,ik->',P.conj(),C4,P)).real/mult
        out.append((w[i]/B,mult,dim,round(chi,3),j-i))
        i=j
    return out
