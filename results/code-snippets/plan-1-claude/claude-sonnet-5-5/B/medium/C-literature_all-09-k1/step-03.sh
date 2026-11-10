cat > /tmp/a.py <<'E'
import math, itertools, random
from math import factorial as f, sqrt
def w3j(j1,j2,j3,m1,m2,m3):
    if m1+m2+m3!=0: return 0.0
    if j3>j1+j2 or j3<abs(j1-j2): return 0.0
    if abs(m1)>j1 or abs(m2)>j2 or abs(m3)>j3: return 0.0
    t=(f(j1+j2-j3)*f(j1-j2+j3)*f(-j1+j2+j3)/f(j1+j2+j3+1))
    t*=f(j1+m1)*f(j1-m1)*f(j2+m2)*f(j2-m2)*f(j3+m3)*f(j3-m3)
    s=0
    for k in range(0,40):
        a=[k,j1+j2-j3-k,j1-m1-k,j2+m2-k,j3-j2+m1+k,j3-j1-m2+k]
        if min(a)<0: continue
        s+=(-1)**k/ (f(a[0])*f(a[1])*f(a[2])*f(a[3])*f(a[4])*f(a[5]))
    return (-1)**(j1-j2-m3)*sqrt(t)*s
def ck(k,m1,m2): # <2 m1|C^k|2 m2>
    return (-1)**m1*5*w3j(2,k,2,0,0,0)*w3j(2,k,2,-m1,m1-m2,m2)
ms=[2,1,0,-1,-2]
def ee(a,b,c,d,F): # <ab|1/r12|cd> orbitals m (spatial) ; electron1 a->c, electron2 b->d
    if a+b!=c+d: return 0.0
    s=0
    for k,Fk in ((0,F[0]),(2,F[2]),(4,F[4])):
        s+=Fk*ck(k,a,c)*ck(k,b,d)*(-1)**(a-c)
    return s
# spin orbitals (m,s) s=0 up,1 down
so=[(m,s) for s in (0,1) for m in ms]
def hmat(Dq):
    h={}
    d={2:1,1:-4,0:6,-1:-4,-2:1}
    for m in ms: h[(m,m)]=d[m]*Dq
    h[(2,-2)]=5*Dq;h[(-2,2)]=5*Dq
    return h
def build(B,C,Dq):
    F={0:0.0,2:49*B+7*C,4:63*C/5}
    h=hmat(Dq)
    dets=[]
    for dn in ms:
        for up in itertools.combinations(ms,4):
            if dn in () : pass
            dets.append((tuple(up),dn))
    # spin orbitals list per det: ups (m,0) ... dn (dn,1)
    def orbs(D): return [(m,0) for m in D[0]]+[(D[1],1)]
    # two-electron antisym integral <ab||cd> for spin orbs
    def J(a,b,c,d):
        v=0
        if a[1]==c[1] and b[1]==d[1]: v+=ee(a[0],b[0],c[0],d[0],F)
        if a[1]==d[1] and b[1]==c[1]: v-=ee(a[0],b[0],d[0],c[0],F)
        return v
    n=len(dets);H=[[0.0]*n for _ in range(n)]
    for i,Di in enumerate(dets):
        oi=orbs(Di)
        for j,Dj in enumerate(dets):
            oj=orbs(Dj)
            si=set(oi);sj=set(oj)
            diff_i=[o for o in oi if o not in sj]; diff_j=[o for o in oj if o not in si]
            nd=len(diff_i)
            if nd>2: continue
            # build ordered lists for sign
            def order(o): return sorted(o,key=lambda x:(x[1],-x[0]))
            li=order(oi); lj=order(oj)
            if nd==0:
                v=0
                for a in li:
                    v+=h.get((a[0],a[0]),0)
                for a,b in itertools.combinations(li,2): v+=J(a,b,a,b)
                H[i][j]=v
            elif nd==1:
                a=diff_i[0];b=diff_j[0]
                # move a to position of b in sequence: sign
                lk=[b if x==a else x for x in li]
                # sign of permutation sorting lk to lj
                perm=[lj.index(x) for x in lk]
                sg=1
                p=perm[:]
                for x in range(len(p)):
                    for y in range(x+1,len(p)):
                        if p[x]>p[y]: sg=-sg
                v=0
                if a[1]==b[1]: v+=h.get((a[0],b[0]),0)
                for c in li:
                    if c!=a: v+=J(a,c,b,c)
                H[i][j]=sg*v
            else:
                a1,a2=diff_i;b1,b2=diff_j
                best=None
                for (x1,x2) in ((b1,b2),(b2,b1)):
                    lk=list(li)
                    lk[lk.index(a1)]=x1;lk[lk.index(a2)]=x2
                    p=[lj.index(x) for x in lk]
                    sg=1
                    for x in range(len(p)):
                        for y in range(x+1,len(p)):
                            if p[x]>p[y]: sg=-sg
                    H[i][j]+=sg*J(a1,a2,x1,x2)*1  # sign relative handled
                # note: J antisym already includes both; avoid double count
                H[i][j]/=1
    return H
E
echo ok