import numpy as np, itertools, math
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*gaunt(2,k,2,-m1,q,m2))*math.sqrt(4*math.pi/(2*k+1))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),6) if sum(1 for o in d if so[o][1]==0)==3]
idx={d:i for i,d in enumerate(dets)}
def act(ops,occ):
    st=list(occ); sign=1
    for op,orb in ops:
        if op=='a':
            if orb not in st: return None,0
            i=st.index(orb); sign*=(-1)**i; st.pop(i)
        else:
            if orb in st: return None,0
            st.insert(0,orb)
            for i in range(len(st)-1):
                if st[i]>st[i+1]: st[i],st[i+1]=st[i+1],st[i]; sign=-sign
    return tuple(st),sign
n=len(dets)
def build_one(V):
    M=np.zeros((n,n))
    for a,d in enumerate(dets):
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=V[so[q][0]+2,so[p][0]+2]
                if v==0: continue
                st,sg=act((('a',p),('c',q)),d)
                if sg: M[idx[st],a]+=sg*v
    return M
def build_two(k):
    M=np.zeros((n,n))
    for a,d in enumerate(dets):
        for t,u in itertools.permutations(d,2):
            for r in range(10):
                for s in range(10):
                    if r==s: continue
                    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[r],so[s],so[t],so[u]
                    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: continue
                    v=CK[(k,m1,m3)]*CK[(k,m4,m2)]
                    if v==0: continue
                    st,sg=act((('a',t),('a',u),('c',s),('c',r)),d)
                    if sg: M[idx[st],a]+=0.5*sg*v
    return M
Vu=np.zeros((5,5))
for m in ms: Vu[m+2,m+2]={0:6,1:-4,-1:-4,2:1,-2:1}[m]
Vu[0,4]=Vu[4,0]=5
HD=build_one(Vu); G2=build_two(2); G4=build_two(4)
S2=np.zeros((n,n))
for a,d in enumerate(dets):
    for p in d:
        if so[p][1]!=1: continue
        st,sg=act((('a',p),('c',p-1)),d)
        if not sg: continue
        for p2 in st:
            if so[p2][1]!=0: continue
            st2,sg2=act((('a',p2),('c',p2+1)),st)
            if sg2: S2[idx[st2],a]+=sg*sg2
def levels(Dq,B,C):
    F2=49*(B+5*C/35); F4=441*C/35
    H=Dq*HD+F2*G2+F4*G4+1e-4*S2
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,ik,kj->j',v,S2,v)
    return w,np.round(s,3)
def singlets(Dq,B,C):
    w,s=levels(Dq,B,C)
    ws=w[np.abs(s)<0.01]
    g=[]
    for x in ws:
        if g and abs(x-g[-1][0])<1e-3: g[-1][1]+=1
        else: g.append([x,1])
    return [(round(a-g[0][0],1),b) for a,b in g]
w,s=levels(0,1000,4000); print(sorted(set(np.round(w-w[0],0)))[:6])
print(singlets(2000,600,2400)[:8])
obs=np.array([16700,26330,35020])
def res(p):
    Dq,B=p; L=singlets(Dq,B,4*B)
    e=[x for x,d in L[1:]][:3]
    return np.array(e)-obs
r=least_squares(res,[1900,600]); print(r.x,res(r.x))
Dq,B=r.x; print(singlets(Dq,B,4*B)[:10])
w,s=levels(Dq,B,4*B); print([(round(w[i]-w[0]),s[i]) for i in range(0,40,3)])
