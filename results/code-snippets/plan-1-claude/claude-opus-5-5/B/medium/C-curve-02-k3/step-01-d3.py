import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=722.;C=3003.
F2=49*B+7*C; F4=63*C/5.  # F2=49B+7C? check: B=F2/49-5F4/441,C=35F4/441
F4=441*C/35; F2=49*(B+5*F4/441)
ms=[-2,-1,0,1,2]
def ck(k,l1,m1,l2,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*(2*l1+1)*gaunt(l1,k,l2,-m1,m1-m2,m2)) if True else 0
# c^k(lm,l'm') = sqrt(4pi/(2k+1)) * int Y*_lm Y_k,m-m' Y_l'm'
def c(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5*0+ (-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
Fk={0:0.,2:F2,4:F4}
def U(a,b,cc,d): # <ab|1/r|cd>, orbital m's
    if a+b!=cc+d: return 0.
    return sum(c(k,a,cc)*c(k,d,b)*Fk[k] for k in (2,4))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def H(Dq):
    V=np.zeros((5,5))
    for i,m in enumerate(ms): V[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    N=len(dets);M=np.zeros((N,N))
    for I,d in enumerate(dets):
        # one-body
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=V[ms.index(so[q][0]),ms.index(so[p][0])]
                if v==0: continue
                if q!=p and q in d: continue
                l=list(d); pos=l.index(p); l[pos]=q
                sign=(-1)**sum(1 for x in l if x<q)  # placeholder
                # compute sign by sorting
                perm=l[:]; sgn=1
                for i in range(len(perm)):
                    for j in range(len(perm)-1-i):
                        if perm[j]>perm[j+1]: perm[j],perm[j+1]=perm[j+1],perm[j]; sgn=-sgn
                M[idx[tuple(perm)],I]+=sgn*v
        # two-body: sum over pairs p<q annihilate, create r,s
        for p,q in itertools.combinations(d,2):
            rest=[x for x in d if x not in (p,q)]
            for r in range(10):
                for s_ in range(10):
                    if r==s_ or r in rest or s_ in rest: continue
                    # amplitude <rs||pq> /2 counted with r,s ordered both ways -> use 1/2
                    (mr,sr),(ms_,ss),(mp,sp),(mq,sq)=so[r],so[s_],so[p],so[q]
                    val=0
                    if sr==sp and ss==sq: val+=U(mr,ms_,mp,mq)
                    if sr==sq and ss==sp: val-=U(mr,ms_,mq,mp)
                    if val==0: continue
                    # state: a_r^+ a_s^+ a_q a_p |d>  (with ordering)
                    l=list(d); sgn=1
                    # remove q then p
                    i=l.index(q); sgn*=(-1)**i; l.pop(i)
                    i=l.index(p); sgn*=(-1)**i; l.pop(i)
                    l.insert(0,s_); l.insert(0,r)
                    perm=l[:]
                    for i in range(len(perm)):
                        for j in range(len(perm)-1-i):
                            if perm[j]>perm[j+1]: perm[j],perm[j+1]=perm[j+1],perm[j]; sgn=-sgn
                    M[idx[tuple(perm)],I]+=0.5*sgn*val
    return M
# operators: S^2, C4 orbital rotation
def S2():
    N=len(dets);M=np.zeros((N,N))
    for I,d in enumerate(dets):
        sz=sum(0.5 if so[x][1]==0 else -0.5 for x in d)
        M[I,I]+=sz*sz+sz
        # S- S+ : S+ flips beta->alpha
        for p in d:
            if so[p][1]!=1: continue
            for q in d:
                if so[q][1]!=1: continue
                # S- S+ = sum_{q,p} a_qb^+ a_qa a_pa^+ a_pb
                pass
    # simpler: build S+ matrix explicitly
    Sp=np.zeros((N,N))
    for I,d in enumerate(dets):
        for p in d:
            if so[p][1]!=1: continue
            q=p-1
            if q in d: continue
            l=list(d); i=l.index(p); l[i]=q
            sgn=1;perm=l[:]
            for a in range(3):
                for b in range(2-a):
                    if perm[b]>perm[b+1]: perm[b],perm[b+1]=perm[b+1],perm[b]; sgn=-sgn
            Sp[idx[tuple(perm)],I]+=sgn
    return M+Sp.T@Sp
def Rot():
    N=len(dets);R=np.zeros((N,N),complex)
    for I,d in enumerate(dets):
        R[I,I]=np.prod([np.exp(-1j*so[x][0]*np.pi/2) for x in d])
    return R
S2m=S2();R=Rot()
for dq in (1.0,2.2,3.5):
    Hm=H(dq*B)
    w,v=np.linalg.eigh(Hm)
    lv=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-6*B: j+=1
        V=v[:,i:j]
        s2=np.trace(V.T@S2m@V).real/(j-i)
        S=(-1+np.sqrt(1+4*s2))/2
        mult=round(2*S+1)
        orb=(j-i)/mult
        ch=np.trace(V.conj().T@R@V).real/mult
        lab={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}.get((round(orb),round(ch)),'?%s %s'%(orb,ch))
        lv.append((w[i],f"{mult}{lab}",j-i)); i=j
    E0=lv[0][0]
    print(dq,[(l,round((e-E0)/B,3)) for e,l,_ in lv[:6]])
