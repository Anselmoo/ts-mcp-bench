import numpy as np, itertools, hashlib
from sympy.physics.wigner import gaunt
B=806.;C=3570.
F4=C*441/35; F2=49*(B+5*F4/441)
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):  # c^k(l m1, l m2)
    return float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5
# check normalization via known c2(2,2;2,2)=-2/7
print(ck(2,2,2), -2/7)
def U(m1,m2,m3,m4): # <m1 m2|1/r|m3 m4>, electron1 m1->m3
    if m1+m2!=m3+m4: return 0.
    s=0
    for k,F in((2,F2),(4,F4)):
        s+=ck(k,m1,m3)*ck(k,m4,m2)*F
    return s
so=[(m,s) for s in (0,1) for m in ms]
dets=list(itertools.combinations(range(10),5))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
# one-body CF matrix
def Vcf(Dq):
    V=np.zeros((5,5));
    for i,m in enumerate(ms):
        V[i,i]={2:1,1:-4,0:6,-1:-4,-2:1}[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    return V
def op1(h):
    H=np.zeros((N,N))
    for d in dets:
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                hv=h[ms.index(so[q][0]),ms.index(so[p][0])]
                if hv==0: continue
                if q!=p and q in d: continue
                l=list(d); pos=l.index(p); l[pos]=q
                sign=(-1)**pos
                srt=sorted(l); # permutation sign
                perm=np.argsort(l); sgn=np.linalg.det(np.eye(5)[perm]) 
                ph=sign*(-1)**srt.index(q)
                H[idx[tuple(srt)],idx[d]]+=hv*ph
    return H
def two():
    H=np.zeros((N,N))
    for d in dets:
        for a,b in itertools.combinations(d,2):
            for c in range(10):
                for e in range(10):
                    if c==e: continue
                    if so[c][1]!=so[a][1] or so[e][1]!=so[b][1]: continue
                    v=U(so[c][0],so[e][0],so[a][0],so[b][0])
                    if v==0: continue
                    # apply a+_c a+_e a_b a_a
                    l=list(d); ph=1
                    for x in (a,b):
                        i=l.index(x); ph*=(-1)**i; l.pop(i)
                    ok=True
                    for x in (e,c):
                        if x in l: ok=False;break
                        l.insert(0,x)
                    if not ok: continue
                    perm=np.argsort(l); ph*=round(np.linalg.det(np.eye(5)[perm]))
                    H[idx[tuple(sorted(l))],idx[d]]+=v*ph
    return H
HC=two(); 
A=op1(Vcf(1.0))
# S^2
def S2():
    Sz=np.diag([sum(0.5 if so[p][1]==0 else -0.5 for p in d) for d in dets])
    Sp=np.zeros((N,N))
    for d in dets:
        for p in d:
            if so[p][1]==1:
                q=p-5
                if q in d: continue
                l=list(d); pos=l.index(p); l[pos]=q
                perm=np.argsort(l); ph=round(np.linalg.det(np.eye(5)[perm]))
                Sp[idx[tuple(sorted(l))],idx[d]]+=ph
    return Sp.T@Sp+Sz@Sz+Sz
SS=S2()
ML=np.array([sum(so[p][0] for p in d) for d in dets])
C4=np.exp(-1j*np.pi/2*ML)
def levels(Dq):
    H=HC+A*Dq*B+1e-7*B*A
    w,v=np.linalg.eigh(H); w=w/B
    out=[];i=0
    while i<N:
        j=i
        while j<N and w[j]-w[i]<1e-4: j+=1
        V=v[:,i:j]; deg=j-i
        s2=np.trace(V.T@SS@V)/deg; S=(-1+np.sqrt(1+4*s2))/2; mult=int(round(2*S+1))
        od=deg//mult; chi=np.real(np.sum(np.conj(V)*(C4[:,None]*V)))/mult
        if od*mult!=deg: lab='?%d'%deg
        else: lab={1:'A1g' if chi>0 else 'A2g',2:'Eg',3:'T1g' if chi>0 else 'T2g'}[od]
        out.append((w[i],'%d%s'%(mult,lab)))
        i=j
    return out
import json
res=[];allL=[]
grid=np.arange(0,4.01,0.05)
for Dq in grid:
    L=levels(Dq); allL.append(L)
for Dq in np.arange(0,4.01,0.5):
    L=levels(Dq); e0=L[0][0]
    print(Dq,[(t,round(e-e0,3)) for e,t in L[:8]])
    res.append({"dq_over_b":float(Dq),"levels":[{"term":t,"e_over_b":round(float(e-e0),3)} for e,t in L[:6]]})
json.dump(res,open('res.json','w'))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.figure(figsize=(7,8))
for k,(Dq,L) in enumerate(zip(grid,allL)):
    e0=L[0][0]
    for e,t in L[:40]:
        col={'6':'k','4':'b','2':'r'}[t[0]]
        plt.plot(Dq,e-e0,'.',color=col,ms=2)
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.title('d5 Oh Tanabe-Sugano, C/B=%.3f'%(C/B));plt.ylim(0,80)
plt.savefig('/tmp/w/diagram.png',dpi=120)
