cat << 'EOF' > /tmp/d3.py
import itertools, math
from math import factorial as f, sqrt
def w3j(j1,j2,j3,m1,m2,m3):
    if m1+m2+m3!=0: return 0.0
    t=lambda x:f(x)
    pre=(-1)**(j1-j2-m3)*sqrt(t(j1+j2-j3)*t(j1-j2+j3)*t(-j1+j2+j3)/t(j1+j2+j3+1)*t(j1+m1)*t(j1-m1)*t(j2+m2)*t(j2-m2)*t(j3+m3)*t(j3-m3))
    s=0
    for k in range(0,100):
        a=[k,j1+j2-j3-k,j1-m1-k,j2+m2-k,j3-j2+m1+k,j3-j1-m2+k]
        if min(a)<0: continue
        s+=(-1)**k/math.prod(t(x) for x in a)
    return pre*s
def ck(k,m1,m2): # c^k(2m1,2m2)
    return (-1)**m1*5*w3j(2,k,2,0,0,0)*w3j(2,k,2,-m1,m1-m2,m2)
def solve(Dq,B,C):
    F={0:0.0,2:(B+C/7)*49,4:C/35*441}
    def g(a,b,c,d): # <a b|c d> spatial m's
        if a+b!=c+d: return 0
        return sum(ck(k,a,c)*ck(k,d,b)*F[k] for k in (0,2,4))
    V={}
    for m in range(-2,3): V[(m,m)]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    V[(2,-2)]=V[(-2,2)]=5*Dq
    so=[(m,s) for m in range(-2,3) for s in (1,-1)]
    dets=[d for d in itertools.combinations(range(10),3) if sum(so[i][1] for i in d)==1]
    idx={d:i for i,d in enumerate(dets)}
    n=len(dets); H=[[0.0]*n for _ in range(n)]
    def one(p,q):
        if so[p][1]!=so[q][1]: return 0
        return V.get((so[p][0],so[q][0]),0)
    def two(p,q,r,s): # <pq|rs>
        if so[p][1]!=so[r][1] or so[q][1]!=so[s][1]: return 0
        return g(so[p][0],so[q][0],so[r][0],so[s][0])
    # generic second quantization apply
    for d in dets:
        j=idx[d]
        # one-body
        for q in d:
            for p in range(10):
                v=one(p,q)
                if v==0: continue
                lst=list(d); pos=lst.index(q)
                if p!=q and p in lst: continue
                lst[pos]=p
                sign=1
                # sort with sign
                arr=lst[:]
                for a in range(3):
                    for b in range(2-a):
                        if arr[b]>arr[b+1]: arr[b],arr[b+1]=arr[b+1],arr[b]; sign=-sign
                H[idx[tuple(arr)]][j]+=sign*v
        for r,s in itertools.combinations(d,2):
            for p in range(10):
                for q in range(10):
                    if p==q: continue
                    v=two(p,q,r,s)-two(p,q,s,r)
                    if v==0: continue
                    rest=[x for x in d if x not in (r,s)]
                    if p in rest or q in rest: continue
                    # state: annihilate r,s then create q,p ; use ordering: a+_p a+_q a_s a_r ; 1/2 sum over p!=q handled by p<q? use full and 0.5
                    lst=list(d)
                    sign=1
                    # annihilate r
                    i=lst.index(r); sign*=(-1)**i; lst.pop(i)
                    i=lst.index(s); sign*=(-1)**i; lst.pop(i)
                    lst.insert(0,q); lst.insert(0,p)
                    arr=lst[:]
                    for a in range(3):
                        for b in range(2-a):
                            if arr[b]>arr[b+1]: arr[b],arr[b+1]=arr[b+1],arr[b]; sign=-sign
                    H[idx[tuple(arr)]][j]+=0.5*sign*v*2/2*2/2  # pairs r<s counted once; sum p,q full -> 0.5 * antisym*... 
    return H
def jacobi(A):
    n=len(A);A=[r[:] for r in A]
    for sweep in range(60):
        off=sum(A[i][j]**2 for i in range(n) for j in range(n) if i!=j)
        if off<1e-14: break
        for p in range(n):
            for q in range(p+1,n):
                if abs(A[p][q])<1e-14: continue
                th=(A[q][q]-A[p][p])/(2*A[p][q]); t=(1 if th>=0 else -1)/(abs(th)+sqrt(th*th+1))
                c=1/sqrt(t*t+1); s=t*c
                for k in range(n):
                    akp,akq=A[k][p],A[k][q]; A[k][p]=c*akp-s*akq; A[k][q]=s*akp+c*akq
                for k in range(n):
                    apk,aqk=A[p][k],A[q][k]; A[p][k]=c*apk-s*aqk; A[q][k]=s*apk+c*aqk
    return sorted(A[i][i] for i in range(n))
import sys
Dq,B,C=map(float,sys.argv[1:])
H=solve(Dq,B,C)
sym=max(abs(H[i][j]-H[j][i]) for i in range(len(H)) for j in range(len(H)))
e=jacobi(H); e=[x-e[0] for x in e]
print(sym); print([round(x,1) for x in e[:20]])
EOF
python3 /tmp/d3.py 2155 657.4 3696