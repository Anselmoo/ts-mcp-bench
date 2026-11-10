python3 - << 'EOF'
import itertools, numpy as np
from sympy.physics.wigner import wigner_3j
l=2
ms=list(range(-2,3))
orbs=[(m,s) for m in ms for s in (1,-1)]
N=len(orbs)
def red(k): return float((-1)**l*(2*l+1)*wigner_3j(l,k,l,0,0,0))
def me(k,m,q,mp): return float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp))*red(k)
def Vel(i,j,kk,ll,F):
    mi,si=orbs[i]; mj,sj=orbs[j]; mk,sk=orbs[kk]; ml,sl=orbs[ll]
    if si!=sk or sj!=sl: return 0.0
    q=mi-mk
    if mj-ml!=-q: return 0.0
    tot=0.0
    for k,Fk in F.items():
        if abs(q)>k: continue
        tot+=Fk*((-1)**(q%2))*me(k,mi,q,mk)*me(k,mj,-q,ml)
    return tot
def ops(F, Dq):
    h=np.zeros((N,N))
    e0=np.zeros(5); e0[2]=1.0
    e2=np.zeros(5); e2[0]=1/np.sqrt(2); e2[4]=1/np.sqrt(2)
    P=np.outer(e0,e0)+np.outer(e2,e2)
    for p,(mp,sp) in enumerate(orbs):
        for q,(mq,sq) in enumerate(orbs):
            if sp==sq: h[p,q]=10*Dq*P[mp+2,mq+2]
    Vt={}
    for i,j,kk,ll in itertools.product(range(N),repeat=4):
        vv=Vel(i,j,kk,ll,F)
        if abs(vv)>1e-12: Vt[(i,j,kk,ll)]=vv
    return h,Vt
def apply_ann(p,st):
    if not (st>>p)&1: return None,0
    return st^(1<<p), (-1)**bin(st&((1<<p)-1)).count('1')
def apply_cre(p,st):
    if (st>>p)&1: return None,0
    return st|(1<<p), (-1)**bin(st&((1<<p)-1)).count('1')
def build(F,Dq,nel=7):
    h,Vt=ops(F,Dq)
    dets=[sum(1<<i for i in c) for c in itertools.combinations(range(N),nel)]
    idx={d:n for n,d in enumerate(dets)}
    D=len(dets)
    H=np.zeros((D,D))
    for n,d in enumerate(dets):
        for p in range(N):
            for q in range(N):
                if h[p,q]==0: continue
                s1,g1=apply_ann(q,d)
                if s1 is None: continue
                s2,g2=apply_cre(p,s1)
                if s2 is None: continue
                H[idx[s2],n]+=h[p,q]*g1*g2
        for (i,j,kk,ll),v in Vt.items():
            s1,g1=apply_ann(kk,d)
            if s1 is None: continue
            s2,g2=apply_ann(ll,s1)
            if s2 is None: continue
            s3,g3=apply_cre(j,s2)
            if s3 is None: continue
            s4,g4=apply_cre(i,s3)
            if s4 is None: continue
            H[idx[s4],n]+=0.5*v*g1*g2*g3*g4
    nup=np.array([sum(1 for p in range(N) if (d>>p)&1 and orbs[p][1]==1) for d in dets])
    return H,nup,dets
B=1.0; C=3699/784; F4=441*C/35; F2=(441*B+5*F4)/9
F={0:0.0,2:F2,4:F4}
def groups(evs,tol=1e-6):
    out=[];i=0
    while i<len(evs):
        j=i
        while j<len(evs) and abs(evs[j]-evs[i])<tol: j+=1
        out.append((i,j)); i=j
    return out
for Dq in [1.45,2.45,3.00]:
    H,nup,dets=build(F,Dq)
    res=[]  # (E, deg, label-type, C4 char, Ms)
    for nu,Ms in [(5,1.5),(4,0.5)]:
        sel=np.where(nup==nu)[0]
        Hs=H[np.ix_(sel,sel)]
        w,V=np.linalg.eigh(Hs)
        # C4z phase per determinant: exp(-i pi/2 * sum m)
        phase=np.array([np.exp(-1j*np.pi/2*sum(orbs[p][0] for p in range(N) if (dets[s]>>p)&1)) for s in sel])
        for a,b in groups(w):
            Vb=V[:,a:b]
            chi=np.trace(Vb.conj().T @ (phase[:,None]*Vb))
            res.append((w[a],b-a,Ms,np.round(chi.real,3),nu))
    res.sort(key=lambda r:r[0])
    gs=None
    # quartet entries from Ms=1.5 with deg; doublet entries from Ms=0.5 with quartet copies removed
    quart=[r for r in res if r[2]==1.5]
    dbl=[r for r in res if r[2]==0.5]
    # remove quartet copies from dbl (same energy, same multiplicity)
    dbl2=[]
    qcopy=[r[0] for r in quart]
    for r in dbl:
        dbl2.append(r)
    print("Dq",Dq)
    print(" quartets (E, deg, C4z char):")
    for r in quart: print("   ",round(r[0]-quart[0][0],4),r[1],r[3])
    print(" M_S=1/2 eigen groups (E rel. quartet gs, deg, C4z char):")
    for r in dbl[:14]: print("   ",round(r[0]-quart[0][0],4),r[1],r[3])
EOF