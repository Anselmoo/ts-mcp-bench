import numpy as np, itertools, os, json
from sympy.physics.wigner import gaunt
B,C=814.,3902.
F4=441*C/35; F2=49*B+7*C
ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    return float((-1)**m*gaunt(2,k,2,-m,m-mp,mp))*np.sqrt(4*np.pi/(2*k+1))
so=[(m,s) for m in ms for s in (0,1)]
n=10
U=np.zeros((n,n,n,n))
for a,(m1,s1) in enumerate(so):
 for b,(m2,s2) in enumerate(so):
  for c,(m3,s3) in enumerate(so):
   for d,(m4,s4) in enumerate(so):
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: continue
    U[a,b,c,d]=sum(F*ck(k,m1,m3)*ck(k,m4,m2) for k,F in ((2,F2),(4,F4)))
Vc=np.zeros((5,5)); Vc[0,0]=Vc[4,4]=1; Vc[2,2]=6; Vc[1,1]=Vc[3,3]=-4; Vc[0,4]=Vc[4,0]=5
dets=list(itertools.combinations(range(n),4)); idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def apply_ops(ops,det):
    occ=list(det); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in occ: return None
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return None
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return sign,tuple(occ)
H1=np.zeros((N,N)); H2=np.zeros((N,N))
nz=[(a,b,c,e) for a,b,c,e in itertools.product(range(n),repeat=4) if abs(U[a,b,c,e])>1e-12]
for j,d in enumerate(dets):
    for a in range(n):
        for b in range(n):
            if so[a][1]!=so[b][1]: continue
            v=Vc[a//2,b//2]
            if v==0: continue
            r=apply_ops([('c',a),('a',b)],d)
            if r: H1[idx[r[1]],j]+=v*r[0]
    for a,b,c,e in nz:
        r=apply_ops([('c',a),('c',b),('a',e),('a',c)],d)
        if r: H2[idx[r[1]],j]+=0.5*U[a,b,c,e]*r[0]
Spm=np.zeros((N,N))
for j,d in enumerate(dets):
    for i in range(5):
        r=apply_ops([('c',2*i+1),('a',2*i)],d)
        if r: Spm[idx[r[1]],j]+=r[0]
Sz=np.diag([sum(0.5 if so[o][1]==1 else -0.5 for o in d) for d in dets])
S2=Spm.T@Spm+Sz@Sz+Sz
C4=np.diag([np.prod([np.exp(1j*np.pi/2*so[o][0]) for o in d]) for d in dets])
lab={1:{1:'A1g',-1:'A2g'},2:{0:'Eg'},3:{1:'T1g',-1:'T2g'}}
sp={0:'1',1:'3',2:'5'}
print('herm',abs(H2-H2.T).max(),abs(H1-H1.T).max())
def solve(x):
    Dq=max(x,1e-7)*B
    w,v=np.linalg.eigh(H2+Dq*H1+1e-9*S2)
    levels=[];i=0
    while i<N:
        j=i
        while j+1<N and w[j+1]-w[i]<1e-4: j+=1
        P=v[:,i:j+1]; deg=j-i+1
        s2=np.trace(P.T@S2@P)/deg; S=int(round((-1+np.sqrt(1+4*s2))/2))
        g=deg//(2*S+1); ch=np.real(np.trace(P.conj().T@C4@P))/(2*S+1)
        levels.append((w[i],sp[S]+lab[g][int(round(ch))],deg))
        i=j+1
    e0=levels[0][0]
    return [(l,(e-e0)/B) for e,l,dg in levels]
out=[]
for x in np.arange(0,4.01,0.5):
    L=solve(x); out.append((float(x),[(l,round(e,4)) for l,e in L[:6]])); print(x,out[-1][1])
json.dump(out,open(os.environ['OUT']+'/res.json','w'))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fine=np.linspace(0,4,161); allE=[[e for l,e in solve(x)] for x in fine]
m=min(len(a) for a in allE); A=np.array([a[:m] for a in allE])
plt.figure(figsize=(7,8))
for k in range(m): plt.plot(fine,A[:,k],'-',lw=0.8,color='k')
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.title('Tanabe-Sugano d4 Oh, B=814, C=3902 cm-1');plt.ylim(0,80)
plt.savefig(os.environ['OUT']+'/diagram.png',dpi=120)
