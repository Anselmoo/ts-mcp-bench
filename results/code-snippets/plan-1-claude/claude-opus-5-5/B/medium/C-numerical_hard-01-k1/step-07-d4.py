import itertools, math
from math import factorial as f
def w3j(j1,j2,j3,m1,m2,m3):
    if m1+m2+m3!=0: return 0.0
    if abs(m1)>j1 or abs(m2)>j2 or abs(m3)>j3: return 0.0
    t=(-1)**(j1-j2-m3)*math.sqrt(f(j1+j2-j3)*f(j1-j2+j3)*f(-j1+j2+j3)/f(j1+j2+j3+1)*f(j1+m1)*f(j1-m1)*f(j2+m2)*f(j2-m2)*f(j3+m3)*f(j3-m3))
    s=0
    for k in range(0,100):
        a=[k,j1+j2-j3-k,j1-k-m1,j2-k+m2,j3-j2+k+m1,j3-j1+k-m2]
        if min(a)<0: continue
        s+=(-1)**k/(f(a[0])*f(a[1])*f(a[2])*f(a[3])*f(a[4])*f(a[5]))
    return t*s
def ck(k,m,mp): return (-1)**m*5*w3j(2,k,2,0,0,0)*w3j(2,k,2,-m,m-mp,mp)
ms=[-2,-1,0,1,2]
def jacobi(A):
    n=len(A);A=[r[:] for r in A]
    for sweep in range(100):
        off=sum(A[i][j]**2 for i in range(n) for j in range(n) if i!=j)
        if off<1e-18: break
        for p in range(n):
            for q in range(p+1,n):
                if abs(A[p][q])<1e-14: continue
                th=(A[q][q]-A[p][p])/(2*A[p][q])
                t=(1 if th>=0 else -1)/(abs(th)+math.sqrt(th*th+1))
                c=1/math.sqrt(t*t+1);s=t*c
                for k in range(n):
                    akp,akq=A[k][p],A[k][q]
                    A[k][p]=c*akp-s*akq;A[k][q]=s*akp+c*akq
                for k in range(n):
                    apk,aqk=A[p][k],A[q][k]
                    A[p][k]=c*apk-s*aqk;A[q][k]=s*apk+c*aqk
    return sorted(A[i][i] for i in range(n))
CK={}
for k in (2,4):
    for m in ms:
        for mp in ms: CK[k,m,mp]=ck(k,m,mp)
def Vcf(m,mp,Dq):
    if m==mp: return {0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    if abs(m-mp)==4: return 5*Dq
    return 0
def g(a,b,c,d,B,C):
    if a[1]!=c[1] or b[1]!=d[1] or a[0]+b[0]!=c[0]+d[0]: return 0
    F2=49*(B+C/7);F4=441*C/35
    return CK[2,a[0],c[0]]*CK[2,d[0],b[0]]*F2+CK[4,a[0],c[0]]*CK[4,d[0],b[0]]*F4
so=[(m,s) for s in (1,-1) for m in ms]
def H(nup,Dq,B,C):
    dets=[c for c in itertools.combinations(range(10),4) if sum(1 for i in c if so[i][1]==1)==nup]
    idx={d:i for i,d in enumerate(dets)}
    n=len(dets);M=[[0.0]*n for _ in range(n)]
    for d in dets:
        i=idx[d]
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=Vcf(so[q][0],so[p][0],Dq)
                if v==0: continue
                if q!=p and q in d: continue
                lst=list(d);k=lst.index(p);sign=(-1)**k;lst.pop(k)
                k=sum(1 for y in lst if y<q);sign*=(-1)**k;lst.insert(k,q)
                M[idx[tuple(lst)]][i]+=sign*v
        for p,q in itertools.combinations(d,2):
            rest=[x for x in d if x not in (p,q)]
            for r in range(10):
                for s in range(r+1,10):
                    if (r in rest) or (s in rest): continue
                    v=g(so[r],so[s],so[p],so[q],B,C)-g(so[r],so[s],so[q],so[p],B,C)
                    if abs(v)<1e-12: continue
                    lst=list(d);sign=1
                    for x in (q,p):
                        k=lst.index(x);sign*=(-1)**k;lst.pop(k)
                    for x in (s,r):
                        k=sum(1 for y in lst if y<x);sign*=(-1)**k;lst.insert(k,x)
                    M[idx[tuple(lst)]][i]+=sign*v
    return M
def triplets(Dq,B,C):
    e1=jacobi(H(3,Dq,B,C)); e2=jacobi(H(4,Dq,B,C))
    for e in e2:
        j=min(range(len(e1)),key=lambda k:abs(e1[k]-e))
        assert abs(e1[j]-e)<1e-6, (e,e1[j]); e1.pop(j)
    return e1
if __name__=="__main__":
    print([round(x,1) for x in jacobi(H(4,0,1000,4000))])
    print(sorted(set(round(x,1) for x in jacobi(H(3,0,1000,4000)))))
    t=triplets(3000,700,3290)
    print([round(x-t[0],1) for x in t])
