import math, itertools
# gaunt via quadrature
def leg(l,m,x):
    # associated legendre P_l^m (m>=0) no CS phase handled here
    pmm=1.0
    if m>0:
        s=math.sqrt((1-x*x)); f=1.0
        for i in range(1,m+1):
            pmm*=-f*s; f+=2
    if l==m: return pmm
    pm1=x*(2*m+1)*pmm
    if l==m+1: return pm1
    for ll in range(m+2,l+1):
        p=((2*ll-1)*x*pm1-(ll+m-1)*pmm)/(ll-m); pmm,pm1=pm1,p
    return pm1
def Y(l,m,x):
    am=abs(m)
    N=math.sqrt((2*l+1)/2*math.factorial(l-am)/math.factorial(l+am))  # phi part handled separately (1/sqrt(2pi))
    v=N*leg(l,am,x)
    if m<0: v*=(-1)**am
    return v
# gauss-legendre nodes
def gl(n):
    xs=[];ws=[]
    for i in range(1,n+1):
        x=math.cos(math.pi*(i-.25)/(n+.5))
        for _ in range(100):
            p0=1;p1=x
            for k in range(2,n+1): p0,p1=p1,((2*k-1)*x*p1-(k-1)*p0)/k
            dp=n*(x*p1-p0)/(x*x-1)
            dx=p1/dp; x-=dx
            if abs(dx)<1e-15:break
        xs.append(x);ws.append(2/((1-x*x)*dp*dp))
    return xs,ws
xs,ws=gl(40)
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.0
    s=0
    for x,w in zip(xs,ws):
        s+=w*Y(2,m,x)*Y(k,q,x)*Y(2,mp,x)
    # phi integral gives 2pi * 1/(2pi)^(3/2)*... : Y=Θ/sqrt(2pi); triple product -> 1/(2pi)^1.5 *2pi
    s*=1/math.sqrt(2*math.pi)
    return s*math.sqrt(4*math.pi/(2*k+1))
ms=[-2,-1,0,1,2]
C={k:{(a,b):ck(k,a,b) for a in ms for b in ms} for k in (0,2,4)}
# check c0 identity
assert abs(C[0][(1,1)]-1)<1e-9
def build(B,Cc,Dq):
    F2=49*B+7*Cc;F4=63*Cc/5
    F={2:F2,4:F4}
    # spin orbitals index (m,s)
    so=[(m,s) for s in (0,1) for m in ms]
    # one-electron
    h1={}
    def h(a,b):
        (m,s),(mp,sp)=a,b
        if s!=sp: return 0.0
        v=0.0
        if m==mp:
            v=-4*Dq
            if m==0: v+=10*Dq
            if abs(m)==2: v+=10*Dq*0.5
        elif abs(m)==2 and abs(mp)==2: v=10*Dq*0.5
        return v
    # coulomb <ab|cd>=sum_k c^k(a,c)c^k(d,b)F^k, spin a=c,b=d
    def g(a,b,c,d):
        if a[1]!=c[1] or b[1]!=d[1]: return 0.0
        if a[0]+b[0]!=c[0]+d[0]: return 0.0
        return sum(C[k][(a[0],c[0])]*C[k][(d[0],b[0])]*F[k] for k in (2,4))
    return so,h,g
def eigs_sector(B,Cc,Dq,nup):
    so,h,g=build(B,Cc,Dq)
    nd=6-nup
    dets=[]
    for u in itertools.combinations(range(5),nup):
        for d in itertools.combinations(range(5,10),nd):
            dets.append(tuple(u)+tuple(d))
    idx={d:i for i,d in enumerate(dets)}
    n=len(dets); H=[[0.0]*n for _ in range(n)]
    # build via second quantization
    def apply(det,ops):
        # ops list of (create?,orb) applied right to left; return sign,newdet
        l=list(det);sg=1
        for cr,o in reversed(ops):
            if cr:
                if o in l: return 0,None
                p=sum(1 for x in l if x<o); sg*=(-1)**p; l.append(o); l.sort()
            else:
                if o not in l: return 0,None
                p=sum(1 for x in l if x<o); sg*=(-1)**p; l.remove(o)
        return sg,tuple(l)
    h1=[[h(so[i],so[j]) for j in range(10)] for i in range(10)]
    gg={}
    for i in range(10):
     for j in range(10):
      for k in range(10):
       for l in range(10):
        v=g(so[i],so[j],so[k],so[l])
        if abs(v)>1e-12: gg[(i,j,k,l)]=v
    for det in dets:
        c=idx[det]
        for i in range(10):
         for j in range(10):
          if h1[i][j]!=0:
            s,nd_=apply(det,[(1,i),(0,j)])
            if s: H[idx[nd_]][c]+=s*h1[i][j]
        for (i,j,k,l),v in gg.items():
            # 1/2 sum <ij|kl> a_i^+ a_j^+ a_l a_k
            s,nd_=apply(det,[(1,i),(1,j),(0,l),(0,k)])
            if s: H[idx[nd_]][c]+=0.5*s*v
    return H
def jacobi(A):
    n=len(A)
    for sweep in range(60):
        off=sum(A[i][j]**2 for i in range(n) for j in range(i+1,n))
        if off<1e-14:break
        for p in range(n):
            for q in range(p+1,n):
                if abs(A[p][q])<1e-13:continue
                th=(A[q][q]-A[p][p])/(2*A[p][q])
                t=(1 if th>=0 else -1)/(abs(th)+math.sqrt(th*th+1))
                c=1/math.sqrt(t*t+1);s=t*c
                for k in range(n):
                    akp=A[k][p];akq=A[k][q]
                    A[k][p]=c*akp-s*akq;A[k][q]=s*akp+c*akq
                for k in range(n):
                    apk=A[p][k];aqk=A[q][k]
                    A[p][k]=c*apk-s*aqk;A[q][k]=s*apk+c*aqk
    return sorted(A[i][i] for i in range(n))
def singlets(B,Dq):
    Cc=4.5*B
    e0=jacobi(eigs_sector(B,Cc,Dq,3)); e1=jacobi(eigs_sector(B,Cc,Dq,4))
    r=e0[:]
    for x in e1:
        j=min(range(len(r)),key=lambda i:abs(r[i]-x)); r.pop(j)
    return r
def bands(B,Dq):
    r=singlets(B,Dq); g=r[0]
    # collapse degeneracies
    lv=[]
    for x in r:
        x-=g
        if not lv or abs(x-lv[-1][0])>1: lv.append([x,1])
        else: lv[-1][1]+=1
    return lv
if __name__=="__main__":
    print(bands(500,2000))
