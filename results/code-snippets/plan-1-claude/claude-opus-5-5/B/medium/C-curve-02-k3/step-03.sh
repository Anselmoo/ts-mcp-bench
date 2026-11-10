
cd $TMPDIR && cat << 'EOF' > d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=722.;C=3003.
F4=441*C/35; F2=49*(B+5*F4/441)
ms=[-2,-1,0,1,2]
def c(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
Fk={2:F2,4:F4}
def U(a,b,cc,d):
    if a+b!=cc+d: return 0.
    return sum(c(k,a,cc)*c(k,d,b)*Fk[k] for k in (2,4))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def srt(l):
    perm=l[:]; sgn=1
    for i in range(len(perm)):
        for j in range(len(perm)-1-i):
            if perm[j]>perm[j+1]: perm[j],perm[j+1]=perm[j+1],perm[j]; sgn=-sgn
    return tuple(perm),sgn
def H(Dq):
    V=np.zeros((5,5))
    for i,m in enumerate(ms): V[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    N=len(dets);M=np.zeros((N,N))
    for I,d in enumerate(dets):
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=V[ms.index(so[q][0]),ms.index(so[p][0])]
                if v==0: continue
                if q!=p and q in d: continue
                l=list(d); l[l.index(p)]=q
                t,s=srt(l); M[idx[t],I]+=s*v
        for p,q in itertools.combinations(d,2):
            rest=[x for x in d if x not in (p,q)]
            for r in range(10):
                for s_ in range(10):
                    if r==s_ or r in rest or s_ in rest: continue
                    (mr,sr),(ms_,ss),(mp,sp),(mq,sq)=so[r],so[s_],so[p],so[q]
                    val=0
                    if sr==sp and ss==sq: val+=U(mr,ms_,mp,mq)
                    if sr==sq and ss==sp: val-=U(mr,ms_,mq,mp)
                    if val==0: continue
                    l=list(d); sgn=1
                    i=l.index(q); sgn*=(-1)**i; l.pop(i)
                    i=l.index(p); sgn*=(-1)**i; l.pop(i)
                    l=[r,s_]+l
                    t,s=srt(l); M[idx[t],I]+=0.5*sgn*s*val
    return M
N=len(dets)
Sz=np.diag([sum(0.5 if so[x][1]==0 else -0.5 for x in d) for d in dets])
Sp=np.zeros((N,N))
for I,d in enumerate(dets):
    for p in d:
        if so[p][1]!=1: continue
        q=p-1
        if q in d: continue
        l=list(d); l[l.index(p)]=q
        t,s=srt(l); Sp[idx[t],I]+=s
S2m=Sp.T@Sp+Sz@Sz+Sz
R=np.diag([np.prod([np.exp(-1j*so[x][0]*np.pi/2) for x in d]) for d in dets])
for dq in (0.0,1.0,2.2,3.5):
    Hm=H(dq*B)
    w,v=np.linalg.eigh(Hm)
    lv=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-6*B: j+=1
        V=v[:,i:j]
        s2=np.trace(V.T@S2m@V)/(j-i)
        S=(-1+np.sqrt(1+4*s2))/2
        mult=round(2*S+1)
        orb=(j-i)/mult
        ch=np.trace(V.conj().T@R@V).real/mult
        lab={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}.get((round(orb),round(ch)),'?%s %s'%(orb,ch))
        lv.append((w[i],f"{mult}{lab}")); i=j
    E0=lv[0][0]
    print(dq,[(l,round((e-E0)/B,3)) for e,l in lv[:7]])
EOF
python3 d3.py
