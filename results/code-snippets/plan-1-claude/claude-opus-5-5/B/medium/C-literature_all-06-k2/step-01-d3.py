import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2; ms=range(-2,3)
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def U(a,b,c,d,F):  # <ab|cd>
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*C[(k,ma,mc)]*C[(k,md,mb)] for k in (0,2,4))
# cubic CF in |m> basis, Dq units
V=np.zeros((5,5)); 
for m in ms: V[m+2,m+2]={0:6,1:-4,-1:-4,2:1,-2:1}[m]
V[0,4]=V[4,0]=5
def H(Dq,B,Cc):
    F={0:0,2:49*B+7*Cc,4:441*Cc/35}
    n=len(dets); M=np.zeros((n,n))
    for i,d in enumerate(dets):
        for j,e in enumerate(dets):
            # one-body
            val=0
            sd,se=set(d),set(e)
            diff_d=sd-se; diff_e=se-sd
            if len(diff_d)==0:
                val+=sum(Dq*V[so[a][0]+2,so[a][0]+2] for a in d if True)
                for a,b in itertools.combinations(d,2):
                    val+=U(a,b,a,b,F)-U(a,b,b,a,F)
            elif len(diff_d)==1:
                a=diff_d.pop(); b=diff_e.pop()
                # sign
                l1=list(d); p1=l1.index(a); l2=list(e); p2=l2.index(b)
                rest=[x for x in d if x!=a]
                sg=(-1)**(p1+p2)
                v=0
                if so[a][1]==so[b][1]: v+=Dq*V[so[a][0]+2,so[b][0]+2]
                for c in rest: v+=U(a,c,b,c,F)-U(a,c,c,b,F)
                val+=sg*v
            elif len(diff_d)==2:
                a1,a2=sorted(diff_d); b1,b2=sorted(diff_e)
                l1=list(d); l2=list(e)
                sg=(-1)**(l1.index(a1)+l1.index(a2)+l2.index(b1)+l2.index(b2))
                val+=sg*(U(a1,a2,b1,b2,F)-U(a1,a2,b2,b1,F))
            M[i,j]=val
    return M
def levels(Dq,B,Cc):
    w=np.linalg.eigvalsh(H(Dq,B,Cc)); w=w-w[0]
    # group degeneracies
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        out.append((round(w[i],1),j-i)); i=j
    return out
Dq=2660;B=529.4
for Cc in (2685,3000,3200):
    print(Cc,levels(Dq,B,Cc)[:6])
