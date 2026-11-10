import numpy as np, itertools, json
from sympy.physics.wigner import gaunt
B=828.;C=3390.
F4=C/35;F2=B+5*F4
Fk={2:49*F2,4:441*F4}
ms=[-2,-1,0,1,2]
def c(k,m,mp): return float((-1)**m*5*gaunt(2,k,2,-m,m-mp,mp))
def Vc(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0.
    return sum(Fk[k]*c(k,m1,m3)*c(k,m4,m2) for k in (2,4))
G=np.zeros((5,)*4)
for a in itertools.product(range(5),repeat=4): G[a]=Vc(*[ms[i] for i in a])
s2=1/np.sqrt(2);idx={m:i for i,m in enumerate(ms)}
U=np.zeros((5,5),complex)
U[0,idx[-2]]=1j*s2;U[0,idx[2]]=-1j*s2
U[1,idx[-1]]=1j*s2;U[1,idx[1]]=1j*s2
U[2,idx[0]]=1
U[3,idx[-1]]=s2;U[3,idx[1]]=-s2
U[4,idx[-2]]=s2;U[4,idx[2]]=s2
Gr=np.einsum('ia,jb,kc,ld,abcd->ijkl',U.conj(),U.conj(),U,U,G)
print("imag",abs(Gr.imag).max()); Gr=Gr.real
dets=[d for d in itertools.combinations(range(10),3) if sum(1-(o%2)*2 for o in d)==1]
di={d:i for i,d in enumerate(dets)}
def ap(ops,d):
    d=list(d);sign=1
    for o,cr in reversed(ops):
        if cr:
            if o in d: return 0,None
            pos=sum(1 for x in d if x<o); d.insert(pos,o); sign*=(-1)**pos
        else:
            if o not in d: return 0,None
            pos=d.index(o); d.pop(pos); sign*=(-1)**pos
    return sign,tuple(d)
def ham(Dq):
    n=len(dets);H=np.zeros((n,n));h=[-4*Dq,-4*Dq,6*Dq,-4*Dq,6*Dq]
    for j,d in enumerate(dets):
        for p in range(5):
            for s in (0,1):
                sg,nd=ap([(2*p+s,1),(2*p+s,0)],d)
                if sg: H[di[nd],j]+=sg*h[p]
        for i,jj,k,l in itertools.product(range(5),repeat=4):
            g=Gr[i,jj,k,l]
            if abs(g)<1e-9: continue
            for s in (0,1):
                for t in (0,1):
                    sg,nd=ap([(2*i+s,1),(2*jj+t,1),(2*l+t,0),(2*k+s,0)],d)
                    if sg: H[di[nd],j]+=0.5*g*sg
    return H
def rot(perm):
    n=len(dets);R=np.zeros((n,n))
    for j,d in enumerate(dets):
        sg=1;new=[]
        for o in d:
            p,s=perm[o//2]; sg*=s; new.append(2*p+o%2)
        sgn=1
        for a in range(3):
            for b in range(a+1,3):
                if new[a]>new[b]: sgn=-sgn
        R[di[tuple(sorted(new))],j]+=sg*sgn
    return R
C4=rot({0:(0,-1),1:(3,1),2:(2,1),3:(1,-1),4:(4,-1)})
C2p=rot({0:(0,1),1:(3,-1),2:(2,1),3:(1,-1),4:(4,-1)})
n=len(dets);S=np.zeros((n,n))
for j,d in enumerate(dets):
    S[j,j]+=0.75
    for p in range(5):
        for q in range(5):
            sg,nd=ap([(2*q+1,1),(2*q,0),(2*p,1),(2*p+1,0)],d)
            if sg: S[di[nd],j]+=sg
def levels(x):
    Dq=max(x,2e-3)*B
    H=ham(Dq)
    # sanity: commutation
    w,v=np.linalg.eigh(H)
    groups=[];i=0
    while i<len(w):
        j=i
        while j+1<len(w) and w[j+1]-w[i]<1e-5*B: j+=1
        groups.append((i,j));i=j+1
    out=[]
    for i,j in groups:
        V=v[:,i:j+1];dim=j-i+1
        s=np.trace(V.T@S@V)/dim; c4=np.trace(V.T@C4@V); c2=np.trace(V.T@C2p@V)
        mult=4 if s>2 else 2
        if dim==1: ir='A1' if c2>0 else 'A2'
        elif dim==2: ir='E'
        elif dim==3: ir='T1' if c2<0 else 'T2'
        else: ir='?%d'%dim
        if dim not in (1,2,3): ir+='[%.2f,%.2f]'%(c4,c2)
        out.append((w[i]/B,'%d%s'%(mult,ir)))
    return out
res=[]
for x in np.arange(0,4.01,0.5):
    L=levels(x);e0=L[0][0]
    L=[(t,e-e0) for e,t in L]
    print(x,[(t,round(e,3)) for t,e in L[:8]])
    res.append({"dq_over_b":float(x),"levels":[{"term":t,"e_over_b":round(float(e),4)} for t,e in L[:6]]})
json.dump(res,open('res.json','w'))
import os;os.environ['MPLCONFIGDIR']='.'
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
xs=np.linspace(0,4,33);data=[levels(x) for x in xs]
fig=plt.figure()
for k in range(8):
    plt.plot(xs,[sorted(e-d[0][0] for e,t in d)[k] for d in data])
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.savefig('diagram.png')
