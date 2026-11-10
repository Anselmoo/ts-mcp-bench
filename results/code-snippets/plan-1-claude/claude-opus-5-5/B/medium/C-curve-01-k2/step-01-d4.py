import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=821.;C=3657.;cb=C/B
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # c^k(l m1, l m2)
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5*gaunt(2,k,2,-m1,m1-m2,m2))
F={0:0.,2:(1+cb/7)*49,4:cb/35*441}  # units of B
spin=[(m,s) for m in ms for s in (0,1)]
n=10
def eri(a,b,c,d): # <ab|cd> spin orbitals
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=spin[a],spin[b],spin[c],spin[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return sum(F[k]*ck(k,ma,mc)*ck(k,md,mb) for k in (2,4) if abs(ma-mc)<=k)
ERI=np.zeros((n,)*4)
for idx in itertools.product(range(n),repeat=4): ERI[idx]=eri(*idx)
def hcf(Dq):
    h=np.zeros((5,5)); d={-2:Dq,-1:-4*Dq,0:6*Dq,1:-4*Dq,2:Dq}
    for i,m in enumerate(ms): h[i,i]=d[m]
    h[0,4]=h[4,0]=5*Dq
    H=np.zeros((n,n))
    for a in range(n):
        for b in range(n):
            if spin[a][1]==spin[b][1]: H[a,b]=h[ms.index(spin[a][0]),ms.index(spin[b][0])]
    return H
dets=list(itertools.combinations(range(n),4)); N=len(dets); ix={d:i for i,d in enumerate(dets)}
def apply_ops(det,ops):
    # ops list of (type,orb) applied right to left; returns sign,det or None
    occ=list(det); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in occ: return None
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return sign,tuple(occ)
def build1(h):
    M=np.zeros((N,N))
    for j,d in enumerate(dets):
        for p in range(n):
            for q in range(n):
                if h[p,q]==0: continue
                r=apply_ops(d,[('c',p),('a',q)])
                if r: M[ix[r[1]],j]+=h[p,q]*r[0]
    return M
H2=np.zeros((N,N))
for j,d in enumerate(dets):
    for p in range(n):
     for q in range(n):
      for r_ in range(n):
       for s in range(n):
        v=ERI[p,q,r_,s]
        if v==0: continue
        r=apply_ops(d,[('c',p),('c',q),('a',s),('a',r_)])
        if r: H2[ix[r[1]],j]+=0.5*v*r[0]
# S^2
Sp=np.zeros((n,n))
for a in range(n):
    m,s=spin[a]
    if s==1: Sp[spin.index((m,0)),a]=1  # s=0 is up? define 0 up,1 down
Spm=build1(Sp); Sz=np.diag([sum(0.5 if spin[o][1]==0 else -0.5 for o in d) for d in dets])
S2=Spm.T@Spm+Sz@Sz+Sz  # S-S+ + Sz^2 + Sz ; Spm raises
# C4 about z: d_m -> exp(i m pi/2) d_m ; determinant phase
C4=np.diag([np.exp(1j*np.pi/2*sum(spin[o][0] for o in d)) for d in dets])
H1cache=build1(hcf(1.0))
for Dq in (0.90,2.15,3.35):
    H=H2+Dq*H1cache
    w,v=np.linalg.eigh(H)
    out=[];i=0
    while i<N:
        j=i
        while j<N and abs(w[j]-w[i])<1e-6: j+=1
        V=v[:,i:j]; s2=np.trace(V.T@S2@V)/(j-i); S=(-1+np.sqrt(1+4*s2))/2
        mult=int(round(2*S+1)); dim=(j-i)//mult
        ch=np.trace(V.conj().T@C4@V).real/mult
        lab={1:('A1' if ch>0 else 'A2'),2:'E',3:('T1' if ch>0 else 'T2')}.get(dim,str(dim))
        out.append((w[i],f"{mult}{lab}",j-i)); i=j
    g=out[0][0]
    print(Dq,[(l,round(e-g,3)) for e,l,_ in out[:5]])
