
cat << 'EOF' > /tmp/d4.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
# ck(k,m1,m2)= sqrt(4pi/(2k+1)) * int Y2m1* Yk(m1-m2) Y2m2
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    # int conj(Y_l1m1) Y_kq Y_l2m2 = (-1)^m1 gaunt(2,k,2,-m1,q,m2)
    return float((-1)**m1*gaunt(2,k,2,-m1,q,m2))*np.sqrt(4*np.pi/(2*k+1))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def eri(a,b,c,d,F):  # <ab|cd> orbitals m, a,c electron1
    if a+b!=c+d: return 0.0
    return sum(F[k]*CK[(k,a,c)]*CK[(k,d,b)] for k in (0,2,4))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),4))
idx={d:i for i,d in enumerate(dets)}
def V1(a,b,Dq):
    if a==b: return {0:6,1:-4,-1:-4,2:1,-2:1}[a]*Dq
    if {a,b}=={2,-2}: return 5*Dq
    return 0
def build(Dq,B,C):
    F4=C/35; F2=B+5*F4
    F={0:0,2:F2*49/49,4:F4}
    # with ck normalized such that F^k Slater: F2(Racah)=F^2/49 -> use F^k
    F={0:0,2:F2*49,4:F4*441}
    N=len(dets); H=np.zeros((N,N))
    for i,D in enumerate(dets):
        for j,E in enumerate(dets):
            if j<i: continue
            Ds=set(D);Es=set(E)
            diff1=[p for p in D if p not in Es]; diff2=[p for p in E if p not in Ds]
            if len(diff1)>2: continue
            def sgn(det,p):
                return (-1)**det.index(p)
            val=0
            if len(diff1)==0:
                for p in D: val+=V1(so[p][0],so[p][0],Dq)
                for p,q in itertools.combinations(D,2):
                    (ma,sa),(mb,sb)=so[p],so[q]
                    val+=eri(ma,mb,ma,mb,F)
                    if sa==sb: val-=eri(ma,mb,mb,ma,F)
            elif len(diff1)==1:
                p=diff1[0];q=diff2[0]
                s=sgn(D,p)*sgn(E,q)
                if so[p][1]==so[q][1]: val+=V1(so[p][0],so[q][0],Dq)
                for r in D:
                    if r==p: continue
                    (ma,sa),(mc,sc),(mr,sr)=so[p],so[q],so[r]
                    if sa==sc: val+=eri(ma,mr,mc,mr,F)
                    if sa==sr and sr==sc: val-=eri(ma,mr,mr,mc,F)
                val*=s
            else:
                p1,p2=diff1;q1,q2=diff2
                # sign: move to front
                Dr=[x for x in D if x not in diff1]; Er=[x for x in E if x not in diff2]
                def perm_sign(lst,target):
                    l=list(lst); s=1
                    for i in range(len(l)):
                        j=l.index(target[i])
                        if j!=i: l[i],l[j]=l[j],l[i]; s=-s
                    return s
                s=perm_sign(D,[p1,p2]+Dr)*perm_sign(E,[q1,q2]+Er)
                (a,sa),(b,sb),(c,sc),(d,sd)=so[p1],so[p2],so[q1],so[q2]
                if sa==sc and sb==sd: val+=eri(a,b,c,d,F)
                if sa==sd and sb==sc: val-=eri(a,b,d,c,F)
                val*=s
            H[i,j]=val;H[j,i]=val
    return H
# Sz=1 dets (3 up 1 down? Sz = (nup-ndn)/2 =1 -> 3 up,1 down); S^2 via restricting Ms=1 and Ms=2
def ms_of(D): return sum(1 if so[p][1]==0 else -1 for p in D)/2
def levels(Dq,B,C):
    H=build(Dq,B,C)
    sel1=[i for i,D in enumerate(dets) if ms_of(D)==1]
    sel2=[i for i,D in enumerate(dets) if ms_of(D)==2]
    e1=np.linalg.eigvalsh(H[np.ix_(sel1,sel1)]); e2=np.linalg.eigvalsh(H[np.ix_(sel2,sel2)])
    # triplet levels = Ms=1 levels minus quintet ones
    e1=list(np.round(e1,4)); 
    for x in np.round(e2,4):
        # remove closest
        k=np.argmin(np.abs(np.array(e1)-x)); e1.pop(k)
    e=np.array(sorted(e1))
    # group
    g=[];
    for x in e:
        if g and abs(x-g[-1][0])<1e-2: g[-1][1]+=1
        else: g.append([x,1])
    return g
import sys
B=float(sys.argv[1]);Dq=float(sys.argv[2])
g=levels(Dq,B,4.3*B)
E0=g[0][0]
for x,n in g[:8]: print(round(x-E0,1),n)
EOF
python3 /tmp/d4.py 700 3000
