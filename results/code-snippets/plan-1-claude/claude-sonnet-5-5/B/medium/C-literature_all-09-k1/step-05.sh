cat > /dev/shm/a.py <<'E'
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
def ck(k,m1,m2):
    return (-1)**m1*5*w3j(2,k,2,0,0,0)*w3j(2,k,2,-m1,m1-m2,m2)
ms=[2,1,0,-1,-2]
def ee(a,b,c,d,F):
    if a+b!=c+d: return 0.0
    return sum(F[k]*ck(k,a,c)*ck(k,d,b) for k in (2,4))
def build(B,C,Dq):
    F={2:49*B+7*C,4:63*C/5}
    dd={2:1,1:-4,0:6,-1:-4,-2:1}
    def h(a,b):
        if a==b: return dd[a]*Dq
        if abs(a)==2 and abs(b)==2: return 5*Dq
        return 0
    dets=[(up,dn) for dn in ms for up in itertools.combinations(ms,4)]
    def orbs(D): return sorted([(m,0) for m in D[0]]+[(D[1],1)],key=lambda x:(x[1],-x[0]))
    def J(a,b,c,d):
        v=0
        if a[1]==c[1] and b[1]==d[1]: v+=ee(a[0],b[0],c[0],d[0],F)
        if a[1]==d[1] and b[1]==c[1]: v-=ee(a[0],b[0],d[0],c[0],F)
        return v
    def sign(lk,lj):
        p=[lj.index(x) for x in lk];sg=1
        for x in range(5):
            for y in range(x+1,5):
                if p[x]>p[y]: sg=-sg
        return sg
    n=len(dets);H=[[0.0]*n for _ in range(n)]
    O=[orbs(D) for D in dets]
    for i in range(n):
        li=O[i]
        for j in range(n):
            lj=O[j]
            di=[o for o in li if o not in lj]; dj=[o for o in lj if o not in li]
            if len(di)>2: continue
            if len(di)==0:
                v=sum(h(a[0],a[0]) for a in li)+sum(J(a,b,a,b) for a,b in itertools.combinations(li,2))
                H[i][j]=v
            elif len(di)==1:
                a=di[0];b=dj[0]
                lk=[b if x==a else x for x in li]
                v=(h(a[0],b[0]) if a[1]==b[1] else 0)+sum(J(a,c,b,c) for c in li if c!=a)
                H[i][j]=sign(lk,lj)*v
            else:
                a1,a2=di;b1,b2=dj
                lk=[b1 if x==a1 else (b2 if x==a2 else x) for x in li]
                H[i][j]=sign(lk,lj)*J(a1,a2,b1,b2)
    return H
def lin(H1,H2,H3,B,C,D):
    n=len(H1);return [[B*H1[i][j]+C*H2[i][j]+D*H3[i][j] for j in range(n)] for i in range(n)]
def jacobi(A):
    n=len(A);A=[r[:] for r in A]
    for sweep in range(60):
        off=sum(A[i][j]**2 for i in range(n) for j in range(n) if i!=j)
        if off<1e-12: break
        for p in range(n):
            for q in range(p+1,n):
                if abs(A[p][q])<1e-14: continue
                th=(A[q][q]-A[p][p])/(2*A[p][q])
                t=(1 if th>=0 else -1)/(abs(th)+sqrt(th*th+1))
                c=1/sqrt(t*t+1);s=t*c
                for k in range(n):
                    akp=A[k][p];akq=A[k][q]
                    A[k][p]=c*akp-s*akq;A[k][q]=s*akp+c*akq
                for k in range(n):
                    apk=A[p][k];aqk=A[q][k]
                    A[p][k]=c*apk-s*aqk;A[q][k]=s*apk+c*aqk
    return sorted(A[i][i] for i in range(n))
HB=build(1,0,0);HC=build(0,1,0);HD=build(0,0,1)
def levels(B,C,D):
    ev=jacobi(lin(HB,HC,HD,B,C,D))
    g=ev[0]; out=[]
    for e in ev:
        e-=g
        if not out or abs(e-out[-1])>1e-3: out.append(e)
    return out
if __name__=="__main__":
    print(levels(860,3850,800)[:8])
E
python3 /dev/shm/a.py