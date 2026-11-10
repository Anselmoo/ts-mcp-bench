
cd $TMPDIR && cat << 'EOF' > d4.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*gaunt(2,k,2,-m1,q,m2))*np.sqrt(4*np.pi/(2*k+1))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def eri(a,b,c,d,F):
    if a+b!=c+d: return 0.0
    return sum(F[k]*CK[(k,a,c)]*CK[(k,d,b)] for k in (0,2,4))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),4))
def V1(a,b,Dq):
    if a==b: return {0:6,1:-4,-1:-4,2:1,-2:1}[a]*Dq
    if {a,b}=={2,-2}: return 5*Dq
    return 0
def perm_sign(lst,target):
    l=list(lst); s=1
    for i in range(len(l)):
        j=l.index(target[i])
        if j!=i: l[i],l[j]=l[j],l[i]; s=-s
    return s
def build(Dq,B,C,sel):
    F4=C/35; F2=B+5*F4
    F={0:0,2:F2*49,4:F4*441}
    D_=[dets[i] for i in sel]; N=len(D_); H=np.zeros((N,N))
    for i,D in enumerate(D_):
        for j,E in enumerate(D_):
            if j<i: continue
            Ds=set(D);Es=set(E)
            diff1=[p for p in D if p not in Es]; diff2=[p for p in E if p not in Ds]
            if len(diff1)>2: continue
            val=0
            if len(diff1)==0:
                for p in D: val+=V1(so[p][0],so[p][0],Dq)
                for p,q in itertools.combinations(D,2):
                    (ma,sa),(mb,sb)=so[p],so[q]
                    val+=eri(ma,mb,ma,mb,F)
                    if sa==sb: val-=eri(ma,mb,mb,ma,F)
            elif len(diff1)==1:
                p=diff1[0];q=diff2[0]
                Dr=[x for x in D if x!=p]
                s=perm_sign(D,[p]+Dr)*perm_sign(E,[q]+Dr)
                if so[p][1]==so[q][1]: val+=V1(so[p][0],so[q][0],Dq)
                for r in Dr:
                    (ma,sa),(mc,sc),(mr,sr)=so[p],so[q],so[r]
                    if sa==sc: val+=eri(ma,mr,mc,mr,F)
                    if sa==sr and sr==sc: val-=eri(ma,mr,mr,mc,F)
                val*=s
            else:
                p1,p2=diff1;q1,q2=diff2
                Dr=[x for x in D if x not in diff1]
                s=perm_sign(D,[p1,p2]+Dr)*perm_sign(E,[q1,q2]+Dr)
                (a,sa),(b,sb),(c,sc),(d,sd)=so[p1],so[p2],so[q1],so[q2]
                if sa==sc and sb==sd: val+=eri(a,b,c,d,F)
                if sa==sd and sb==sc: val-=eri(a,b,d,c,F)
                val*=s
            H[i,j]=val;H[j,i]=val
    return H
def ms_of(D): return sum(1 if so[p][1]==0 else -1 for p in D)/2
sel1=[i for i,D in enumerate(dets) if ms_of(D)==1]
sel2=[i for i,D in enumerate(dets) if ms_of(D)==2]
sel0=[i for i,D in enumerate(dets) if ms_of(D)==0]
def levels(Dq,B,C,singlets=False):
    e1=list(np.round(np.linalg.eigvalsh(build(Dq,B,C,sel1)),3))
    for x in np.round(np.linalg.eigvalsh(build(Dq,B,C,sel2)),3):
        e1.pop(int(np.argmin(np.abs(np.array(e1)-x))))
    e=sorted(e1)
    g=[]
    for x in e:
        if g and abs(x-g[-1][0])<0.05: g[-1][1]+=1
        else: g.append([x,1])
    return g
EOF
cat > run.py << 'EOF'
import sys; sys.path.insert(0,'.')
from d4 import *
B=float(sys.argv[1]);Dq=float(sys.argv[2])
g=levels(Dq,B,4.3*B); E0=g[0][0]
for x,n in g[:8]: print(round(x-E0,1),n)
EOF
python3 run.py 1000 0.0001 | head; echo; python3 run.py 600 3000
