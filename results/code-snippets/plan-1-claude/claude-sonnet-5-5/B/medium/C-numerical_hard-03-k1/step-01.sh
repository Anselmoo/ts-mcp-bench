
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # <2m1|C^k|2m2>
    return float((-1)**m1*gaunt(2,k,2,-m1,m1-m2,m2)*np.sqrt(5)) if False else float((-1)**m1*5*gaunt(2,2,k,-m1,m2,m1-m2)*0+0)
from sympy import Rational
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
C={(k,a,b):c(k,a,b) for k in (0,2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),5) if sum(so[i][1] for i in d)==2 or True]
dets=[d for d in dets if sum(1 if so[i][1] else -1 for i in d)==1]
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def build(Dq,B,Cc):
    F2=49*B+7*Cc;F4=63*Cc/5
    F={0:0,2:F2,4:F4}
    # two-electron <ab|cd> direct: spin orbitals
    def V(a,b,c_,d):
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c_],so[d]
        if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
        return sum(C[(k,ma,mc)]*C[(k,md,mb)]*F[k]/1 for k in (2,4))*0+sum(C[(k,mc,ma)]*C[(k,mb,md)]*F[k] for k in (2,4))*(1)
    # one-electron
    # real orbitals: eg dz2,dx2-y2 ; t2 others. Dq: eg +6Dq, t2 -4Dq
    s=1/np.sqrt(2)
    def vec(d):
        v=np.zeros(5,complex)
        for m,x in d.items(): v[m+2]=x
        return v
    eg=[vec({0:1}),vec({2:s,-2:s})]
    t2=[vec({2:s,-2:-s}),vec({1:s,-1:-s}),vec({1:s,-1:s})]
    h=sum(6*Dq*np.outer(v,v.conj()) for v in eg)+sum(-4*Dq*np.outer(v,v.conj()) for v in t2)
    H=np.zeros((N,N),complex)
    for d in dets:
        i=idx[d]
        for a in d:
            for b in range(10):
                if so[a][1]!=so[b][1]: continue
                hv=h[so[b][0]+2,so[a][0]+2]
                if abs(hv)<1e-12: continue
                if b in d and b!=a: continue
                l=list(d);pos=l.index(a);l[pos]=b
                sign=1
                nd=tuple(sorted(l))
                # sign from sorting
                perm=sum(1 for x in range(5) for y in range(x+1,5) if l[x]>l[y])
                H[idx[nd],i]+=hv*(-1)**perm
    # two-electron via explicit second quantization
    for d in dets:
        i=idx[d]
        for p in range(5):
         for q in range(p+1,5):
          a,b=d[p],d[q]
          for c_ in range(10):
           for e in range(10):
            if c_==e: continue
            ma,mb=so[a],so[b]
            if so[c_][1]+so[e][1]!=ma[1]+mb[1]: continue
            if so[c_][0]+so[e][0]!=ma[0]+mb[0]: continue
            # operator 1/2 sum <cd|a b> c+_c c+_e c_b c_a ... use pair a<b -> (c,e) ordered pair counted both
            l=[x for x in d if x not in(a,b)]
            if c_ in l or e in l: continue
            # amplitude <c e|V|a b>-<c e|V|b a>, sum over c<e only
            if c_>e: continue
            amp=V(c_,e,a,b)-V(c_,e,b,a)
            if abs(amp)<1e-12: continue
            # build state: remove a,b (from positions) then add c,e with sign
            lst=list(d)
            # sign: apply c_b c_a on d: sign
            s1=(-1)**(p+(q-1))
            rest=[x for x in d if x not in(a,b)]
            # c+_c c+_e acting... order: c+_c c+_e c_b c_a ; result det ordered
            seq=[c_,e]+rest
            perm=sum(1 for x in range(5) for y in range(x+1,5) if seq[x]>seq[y])
            nd=tuple(sorted(seq))
            H[idx[nd],i]+=amp*s1*(-1)**perm
    return H
# spin: S^2
def S2():
    M=np.zeros((N,N))
    for d in dets:
        i=idx[d]
        nb=sum(1 for x in d if so[x][1]==0);na=5-nb
        M[i,i]+=((na-nb)/2)**2+(na+nb)/2*0+ (na-nb)/2 + nb
        # S- S+ = nb - pairs.. use S^2=Sz^2+Sz+S-S+ ; S-S+ = sum over spin-down orbs whose up partner empty -> flips
        for a in d:
            if so[a][1]==0:
                pass
    return M
def levels(Dq,B,Cc):
    H=build(Dq,B,Cc)
    assert np.allclose(H,H.conj().T,atol=1e-6),np.abs(H-H.conj().T).max()
    w=np.linalg.eigvalsh(H);return w
if __name__=="__main__":
    w=levels(3000/10,800,3680)
    print(np.round(w[:40]-w[0]))
E
python3 /tmp/a.py
