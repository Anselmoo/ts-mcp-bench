
python3 - << 'EOF' 2>&1 | tail -8
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N
B=800.;C=3473.
F4=C/35; F2=B+5*F4
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float(N(gaunt(2,k,2,-m1,q,m2)))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))
R={2:49*F2,4:441*F4}
Ut={}
for a,b,c,d in itertools.product(ms,repeat=4):
    Ut[a,b,c,d]=0. if a+b!=c+d else sum(R[k]*ck(k,a,c)*ck(k,d,b) for k in (2,4))
so=[(m,s) for m in ms for s in (0,1)]
states=list(itertools.combinations(range(10),5)); idx={s:i for i,s in enumerate(states)}
n=len(states)
def move(st,p,q):
    st1=list(st); sg=(-1)**st1.index(p); st1.remove(p); st1=sorted(st1+[q]); sg*=(-1)**st1.index(q); return tuple(st1),sg
def H(Dq):
    cf={0:6*Dq,1:-4*Dq,-1:-4*Dq,2:Dq,-2:Dq}
    M=np.zeros((n,n))
    for i,st in enumerate(states):
        for p in st: M[i,i]+=cf[so[p][0]]
        for p in st:
            m,s=so[p]
            if abs(m)==2:
                q=so.index((-m,s))
                if q not in st:
                    t,sg=move(st,p,q); M[idx[t],i]+=5*Dq*sg
        for x,y in itertools.combinations(st,2):
            rest=[p for p in st if p not in (x,y)]
            sgn0=(-1)**(st.index(x)+st.index(y)-1)
            for r,t in itertools.combinations(range(10),2):
                if r in rest or t in rest: continue
                (ma,sa),(mb,sb)=so[r],so[t];(mc,sc),(md,sd)=so[x],so[y]
                v=0.
                if sa==sc and sb==sd: v+=Ut[ma,mb,mc,md]
                if sa==sd and sb==sc: v-=Ut[ma,mb,md,mc]
                if abs(v)<1e-12: continue
                new=sorted(rest+[r,t]); sg=sgn0*(-1)**(new.index(r)+new.index(t)-1)
                M[idx[tuple(new)],i]+=v*sg
    return M
def S2():
    M=np.zeros((n,n))
    for i,st in enumerate(states):
        nu=sum(1 for p in st if so[p][1]==0); Sz=(nu-(5-nu))/2
        M[i,i]+=Sz*Sz+Sz
        for p in st:
            m,s=so[p]
            if s==1:
                q=so.index((m,0))
                if q in st: continue
                st1,sg=move(st,p,q)
                for p2 in st1:
                    m2,s2=so[p2]
                    if s2==0:
                        q2=so.index((m2,1))
                        if q2 in st1: continue
                        st2,sg2=move(st1,p2,q2)
                        M[idx[st2],i]+=sg*sg2
    return M
S2M=S2()
c4=np.array([np.prod([np.exp(1j*np.pi/2*so[p][0]) for p in st]) for st in states])
for x in (0,1.45,2.55,3.25,2.7,2.8):
    w,v=np.linalg.eigh(H(x*B))
    groups=[];i=0
    while i<n:
        j=i
        while j<n and w[j]-w[i]<1e-3: j+=1
        V=v[:,i:j]; s2=np.trace(V.T@S2M@V)/(j-i); S=(-1+np.sqrt(1+4*s2))/2
        ch=np.trace(V.conj().T@(c4[:,None]*V)).real/(2*S+1)
        groups.append((round((w[i]-w[0])/B,3),j-i,round(2*S+1),round(ch,2)));i=j
    print(x,groups[:5])
EOF
