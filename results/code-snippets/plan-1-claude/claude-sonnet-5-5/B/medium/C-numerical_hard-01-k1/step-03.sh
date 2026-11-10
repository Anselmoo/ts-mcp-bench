cat > /tmp/a.py <<'E'
import math, itertools
from math import factorial as f, sqrt
def w3j(j1,j2,j3,m1,m2,m3):
    if m1+m2+m3!=0: return 0
    if j3<abs(j1-j2) or j3>j1+j2: return 0
    if abs(m1)>j1 or abs(m2)>j2 or abs(m3)>j3: return 0
    t=(-1)**(j1-j2-m3)*sqrt(f(j1+j2-j3)*f(j1-j2+j3)*f(-j1+j2+j3)/f(j1+j2+j3+1))
    t*=sqrt(f(j1+m1)*f(j1-m1)*f(j2+m2)*f(j2-m2)*f(j3+m3)*f(j3-m3))
    s=0
    for k in range(0,j1+j2+j3+2):
        a=[k,j1+j2-j3-k,j1-m1-k,j2+m2-k,j3-j2+m1+k,j3-j1-m2+k]
        if min(a)<0: continue
        d=1
        for x in a:d*=f(x)
        s+=(-1)**k/d
    return t*s
l=2
def c(k,m,mp):
    q=m-mp
    return (-1)**m*5*w3j(2,k,2,-m,q,mp)*w3j(2,k,2,0,0,0)
def build(B,C,Dq):
    F={0:0,2:49*B+7*C,4:12.6*C}
    # spin orbitals index: (m,s)
    so=[(m,s) for m in range(-2,3) for s in (0,1)]
    idx={x:i for i,x in enumerate(so)}
    def V(a,b,cc,d): # <ab|cd> m values
        return sum(c(k,a,cc)*c(k,d,b)*F[k] for k in (0,2,4))
    cf={(0,0):6*Dq,(1,1):-4*Dq,(-1,-1):-4*Dq,(2,2):Dq,(-2,-2):Dq,(2,-2):5*Dq,(-2,2):5*Dq}
    return so,idx,V,cf
def apply(op_list,state):
    pass
def spec(B,C,Dq,Ms2):
    so,idx,V,cf=build(B,C,Dq)
    n=len(so)
    nu=(4+Ms2)//2; nd=4-nu
    dets=[]
    for u in itertools.combinations(range(5),nu):
        for d in itertools.combinations(range(5),nd):
            dets.append(tuple(sorted([2*(x-2+2) for x in u]+[2*x+1 for x in d])))
    # orbital index i -> m=i//2-2, spin i%2
    di={d:i for i,d in enumerate(dets)}
    N=len(dets)
    H=[[0.0]*N for _ in range(N)]
    def ann(i,det):
        if i not in det: return None
        p=det.index(i); return (-1)**p, tuple(x for x in det if x!=i)
    def cre(i,det):
        if i in det: return None
        p=sum(1 for x in det if x<i); return (-1)**p, tuple(sorted(det+(i,)))
    M=lambda i:i//2-2
    S=lambda i:i%2
    for col,det in enumerate(dets):
        for i in range(10):
            for j in range(10):
                if S(i)!=S(j): continue
                h=cf.get((M(i),M(j)),0)
                if h==0: continue
                r=ann(j,det)
                if not r: continue
                r2=cre(i,r[1])
                if not r2: continue
                H[di[r2[1]]][col]+=h*r[0]*r2[0]
        for p in range(10):
         for q in range(10):
          if p==q: continue
          for r_ in range(10):
           for s in range(10):
            if r_==s: continue
            if S(p)!=S(r_) or S(q)!=S(s): continue
            if M(p)+M(q)!=M(r_)+M(s): continue
            v=V(M(p),M(q),M(r_),M(s))
            if abs(v)<1e-12: continue
            # 1/2 v a+p a+q a_s a_r
            x=ann(r_,det)
            if not x: continue
            y=ann(s,x[1])
            if not y: continue
            z=cre(q,y[1])
            if not z: continue
            w=cre(p,z[1])
            if not w: continue
            H[di[w[1]]][col]+=0.5*v*x[0]*y[0]*z[0]*w[0]
    return H
def jacobi(A):
    n=len(A);A=[r[:] for r in A]
    for sweep in range(100):
        off=sum(A[i][j]**2 for i in range(n) for j in range(i))
        if off<1e-16:break
        for p in range(n):
            for q in range(p+1,n):
                if abs(A[p][q])<1e-14:continue
                th=(A[q][q]-A[p][p])/(2*A[p][q])
                t=(1 if th>=0 else -1)/(abs(th)+sqrt(th*th+1))
                cs=1/sqrt(t*t+1);sn=t*cs
                for k in range(n):
                    a,b=A[k][p],A[k][q];A[k][p]=cs*a-sn*b;A[k][q]=sn*a+cs*b
                for k in range(n):
                    a,b=A[p][k],A[q][k];A[p][k]=cs*a-sn*b;A[q][k]=sn*a+cs*b
    return sorted(A[i][i] for i in range(n))
def levels(B,C,Dq):
    e1=jacobi(spec(B,C,Dq,2)); e2=jacobi(spec(B,C,Dq,4))
    e1=e1[:]
    for q in e2:
        # remove nearest
        k=min(range(len(e1)),key=lambda i:abs(e1[i]-q)); e1.pop(k)
    # cluster
    out=[];
    for e in e1:
        if out and abs(e-out[-1][0])<1e-3: out[-1][1]+=1
        else: out.append([e,1])
    return out
if __name__=="__main__":
    L=levels(700,700*4.7,2000)
    g=L[0][0]
    print([(round(e-g,1),d) for e,d in L][:12])
E
python3 /tmp/a.py