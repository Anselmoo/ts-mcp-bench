import itertools, math, sys
from math import factorial as t, sqrt
def w3j(j1,j2,j3,m1,m2,m3):
    if m1+m2+m3!=0: return 0.0
    pre=(-1)**(j1-j2-m3)*sqrt(t(j1+j2-j3)*t(j1-j2+j3)*t(-j1+j2+j3)/t(j1+j2+j3+1)*t(j1+m1)*t(j1-m1)*t(j2+m2)*t(j2-m2)*t(j3+m3)*t(j3-m3))
    s=0
    for k in range(0,20):
        a=[k,j1+j2-j3-k,j1-m1-k,j2+m2-k,j3-j2+m1+k,j3-j1-m2+k]
        if min(a)<0: continue
        s+=(-1)**k/math.prod(t(x) for x in a)
    return pre*s
def ck(k,m1,m2): return (-1)**m1*5*w3j(2,k,2,0,0,0)*w3j(2,k,2,-m1,m1-m2,m2)
def srt(arr):
    arr=list(arr); sign=1
    for a in range(len(arr)):
        for b in range(len(arr)-1-a):
            if arr[b]>arr[b+1]: arr[b],arr[b+1]=arr[b+1],arr[b]; sign=-sign
    return tuple(arr),sign
def build(Dq,B,C):
    F={0:0.0,2:(B+C/7)*49,4:C/35*441}
    def g(a,b,c,d):
        if a+b!=c+d: return 0
        return sum(ck(k,a,c)*ck(k,d,b)*F[k] for k in (0,2,4))
    V={}
    for m in range(-2,3): V[(m,m)]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    V[(2,-2)]=V[(-2,2)]=5*Dq
    so=[(m,s) for m in range(-2,3) for s in (1,-1)]
    dets=[d for d in itertools.combinations(range(10),3) if sum(so[i][1] for i in d)==1]
    idx={d:i for i,d in enumerate(dets)}; n=len(dets); H=[[0.0]*n for _ in range(n)]
    def two(p,q,r,s):
        if so[p][1]!=so[r][1] or so[q][1]!=so[s][1]: return 0
        return g(so[p][0],so[q][0],so[r][0],so[s][0])
    for d in dets:
        j=idx[d]
        for q in d:
            for p in range(10):
                if so[p][1]!=so[q][1]: continue
                v=V.get((so[p][0],so[q][0]),0)
                if v==0: continue
                lst=list(d)
                if p!=q and p in lst: continue
                lst[lst.index(q)]=p
                arr,sg=srt(lst); H[idx[arr]][j]+=sg*v
        for r,s in itertools.combinations(d,2):
            rest=[x for x in d if x not in (r,s)]
            for p in range(10):
                for q in range(10):
                    if p==q or p in rest or q in rest: continue
                    v=two(p,q,r,s)-two(p,q,s,r)
                    if v==0: continue
                    lst=list(d); sign=1
                    i=lst.index(r); sign*=(-1)**i; lst.pop(i)
                    i=lst.index(s); sign*=(-1)**i; lst.pop(i)
                    arr,sg=srt([p,q]+lst); H[idx[arr]][j]+=0.5*sign*sg*v
    return H
def jacobi(A):
    n=len(A);A=[r[:] for r in A]
    for sweep in range(60):
        off=sum(A[i][j]**2 for i in range(n) for j in range(n) if i!=j)
        if off<1e-12: break
        for p in range(n):
            for q in range(p+1,n):
                if abs(A[p][q])<1e-13: continue
                th=(A[q][q]-A[p][p])/(2*A[p][q]); tt=(1 if th>=0 else -1)/(abs(th)+sqrt(th*th+1))
                c=1/sqrt(tt*tt+1); s=tt*c
                for k in range(n):
                    akp,akq=A[k][p],A[k][q]; A[k][p]=c*akp-s*akq; A[k][q]=s*akp+c*akq
                for k in range(n):
                    apk,aqk=A[p][k],A[q][k]; A[p][k]=c*apk-s*aqk; A[q][k]=s*apk+c*aqk
    return sorted(A[i][i] for i in range(n))
Dq,B,C=map(float,sys.argv[1:])
e=jacobi(build(Dq,B,C)); e=[x-e[0] for x in e]
out=[]; 
for x in e:
    if not out or abs(x-out[-1][0])>0.05: out.append([x,1])
    else: out[-1][1]+=1
print([(round(a,1),b) for a,b in out])
