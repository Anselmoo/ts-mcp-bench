
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N
B=800.;C=3473.
F4=C/35; F2=B+5*F4
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # <l m1|C^k_{m1-m2}|l m2>
    q=m1-m2
    if abs(q)>k: return 0.
    return float(N(gaunt(2,k,2,-m1,q,m2)))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5
R={0:0.,2:F2,4:F4}
# <ab|1/r|cd>, spatial
def U(a,b,c,d):
    if a+b!=c+d: return 0.
    return sum(R[k]*ck(k,a,c)*ck(k,d,b) for k in (2,4))
Ut={}
for a,b,c,d in itertools.product(ms,repeat=4): Ut[a,b,c,d]=U(a,b,c,d)
so=[(m,s) for m in ms for s in (0,1)]
states=list(itertools.combinations(range(10),5)); idx={s:i for i,s in enumerate(states)}
n=len(states)
def H(Dq):
    cf={0:6*Dq,1:-4*Dq,-1:-4*Dq,2:Dq,-2:Dq}
    M=np.zeros((n,n))
    for i,st in enumerate(states):
        for p in st: M[i,i]+=cf[so[p][0]]
        # cf off diag 2<->-2
        for p in st:
            m,s=so[p]
            if abs(m)==2:
                q=so.index((-m,s))
                if q not in st:
                    new=list(st); new.remove(p); 
                    sign=(-1)**st.index(p); new2=sorted(new+[q]); sign*=(-1)**new2.index(q)
                    M[idx[tuple(new2)],i]+=5*Dq*sign
        # two-electron
        for x,y in itertools.combinations(st,2):
            rest=[p for p in st if p not in (x,y)]
            sgn0=(-1)**(st.index(x)+st.index(y)-1)
            for r,t in itertools.permutations(range(10),2):
                if r in rest or t in rest: continue
                if r>t: continue
                # <rt|V|xy> antisym
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
        nu=sum(1 for p in st if so[p][1]==0); nd=5-nu; Sz=(nu-nd)/2
        M[i,i]+=Sz*Sz+Sz+ nd  # S-S+ diag ... use S^2=S-S+ + Sz^2 + Sz
        # S-S+: move down->up then up->down
        for p in st:
            m,s=so[p]
            if s==1:
                q=so.index((m,0))
                if q in st: continue
                st1=list(st); sg=(-1)**st1.index(p); st1.remove(p); st1=sorted(st1+[q]); sg*=(-1)**st1.index(q)
                for p2 in st1:
                    m2,s2=so[p2]
                    if s2==0:
                        q2=so.index((m2,1))
                        if q2 in st1: continue
                        st2=list(st1); sg2=sg*(-1)**st2.index(p2); st2.remove(p2); st2=sorted(st2+[q2]); sg2*=(-1)**st2.index(q2)
                        if tuple(st2)==st: continue
                        M[idx[tuple(st2)],i]+=sg2
    return M
S2M=S2()
c4=np.array([np.prod([np.exp(1j*np.pi/2*so[p][0]) for p in st]) for st in states])
for x in (1.45,2.55,3.25):
    w,v=np.linalg.eigh(H(x*B))
    # group
    groups=[];i=0
    while i<n:
        j=i
        while j<n and w[j]-w[i]<1e-3: j+=1
        V=v[:,i:j]; s2=np.trace(V.T@S2M@V)/(j-i); S=(-1+np.sqrt(1+4*s2))/2
        ch=np.trace(V.conj().T@(c4[:,None]*V)).real/(2*S+1)
        groups.append(((w[i]-w[0])/B,j-i,round(2*S+1),round(ch,2)));i=j
    print(x,groups[:5])
EOF
python3 /tmp/d5.py
