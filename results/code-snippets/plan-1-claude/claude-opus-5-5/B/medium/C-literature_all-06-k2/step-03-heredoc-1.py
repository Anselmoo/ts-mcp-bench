import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=range(-2,3)
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
def U(a,b,c,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*C[(k,ma,mc)]*C[(k,md,mb)] for k in (0,2,4))
V=np.zeros((5,5))
for m in ms: V[m+2,m+2]={0:6,1:-4,-1:-4,2:1,-2:1}[m]
V[0,4]=V[4,0]=5
def H(Dq,B,Cc):
    F={0:0,2:49*B+7*Cc,4:441*Cc/35}
    n=len(dets); M=np.zeros((n,n))
    for i,d in enumerate(dets):
        for j,e in enumerate(dets):
            sd,se=set(d),set(e); dd=sorted(sd-se); de=sorted(se-sd); val=0
            if not dd:
                val+=sum(Dq*V[so[a][0]+2,so[a][0]+2] for a in d)
                for a,b in itertools.combinations(d,2): val+=U(a,b,a,b,F)-U(a,b,b,a,F)
            elif len(dd)==1:
                a=dd[0];b=de[0]; sg=(-1)**(d.index(a)+e.index(b)); v=0
                if so[a][1]==so[b][1]: v+=Dq*V[so[a][0]+2,so[b][0]+2]
                for c in d:
                    if c!=a: v+=U(a,c,b,c,F)-U(a,c,c,b,F)
                val=sg*v
            elif len(dd)==2:
                a1,a2=dd;b1,b2=de
                sg=(-1)**(d.index(a1)+d.index(a2)+e.index(b1)+e.index(b2))
                val=sg*(U(a1,a2,b1,b2,F)-U(a1,a2,b2,b1,F))
            M[i,j]=val
    return M
def levels(Dq,B,Cc):
    w=np.linalg.eigvalsh(H(Dq,B,Cc)); w=w-w[0]; out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        out.append((round(w[i],1),j-i)); i=j
    return out
for Cc in (2685,3000,3200):
    print(Cc,levels(2660,529.4,Cc)[:6])
