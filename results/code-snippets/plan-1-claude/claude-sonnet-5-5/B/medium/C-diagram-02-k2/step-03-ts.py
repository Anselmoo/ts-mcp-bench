import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N
B=814.;C=3902.
F2=49*B+7*C;F4=63*C/5
ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.
    g=float(N(gaunt(2,k,2,-m,q,mp)))
    return (-1)**m*np.sqrt(4*np.pi/(2*k+1))*g
c={k:np.array([[ck(k,m,mp) for mp in ms] for m in ms]) for k in (2,4)}
Vc=np.zeros((5,)*4)
for a in range(5):
 for b in range(5):
  for cc in range(5):
   for d in range(5):
    if ms[a]+ms[b]!=ms[cc]+ms[d]: continue
    Vc[a,b,cc,d]=sum(F*c[k][a,cc]*c[k][d,b] for k,F in ((2,F2),(4,F4)))
# real orbitals z2,xz,yz,x2-y2,xy ; columns = coefficients over m=-2..2
T=np.zeros((5,5),complex)
s=1/np.sqrt(2)
idx={m:i for i,m in enumerate(ms)}
T[idx[0],0]=1
T[idx[-1],1]=s;T[idx[1],1]=-s
T[idx[-1],2]=1j*s;T[idx[1],2]=1j*s
T[idx[2],3]=s;T[idx[-2],3]=s
T[idx[2],4]=-1j*s;T[idx[-2],4]=1j*s
# V_real[ab|cd]=sum conj(T[a'a])conj(T[b'b])T[c'c]T[d'd]V[a'b'c'd']
Vr=np.einsum('ia,jb,kc,ld,ijkl->abcd',T.conj(),T.conj(),T,T,Vc)
assert abs(Vr.imag).max()<1e-6; Vr=Vr.real
Uc=np.diag([np.exp(-1j*m*np.pi/2) for m in ms]); U4=T.conj().T@Uc@T
dets=[sum(1<<i for i in comb) for comb in itertools.combinations(range(10),4)]
di={d:i for i,d in enumerate(dets)}
def ap(p,q,d):  # a†_p a_q
    if not d>>q&1: return None
    sg=(-1)**bin(d&((1<<q)-1)).count('1'); d^=1<<q
    if d>>p&1: return None
    sg*=(-1)**bin(d&((1<<p)-1)).count('1'); return sg,d|1<<p
def onebody(h): # h spin-orbital matrix 10x10
    M=np.zeros((210,210),complex)
    for d in dets:
        for p in range(10):
         for q in range(10):
          if h[p,q]!=0:
            r=ap(p,q,d)
            if r: M[di[r[1]],di[d]]+=h[p,q]*r[0]
    return M
# spin orbital index 2*i+s
H2=np.zeros((210,210))
def a_(p,d,dag):
    if dag:
        if d>>p&1: return None
        sg=(-1)**bin(d&((1<<p)-1)).count('1'); return sg,d|1<<p
    if not d>>p&1: return None
    sg=(-1)**bin(d&((1<<p)-1)).count('1'); return sg,d^(1<<p)
for d in dets:
 for a in range(5):
  for b in range(5):
   for cc in range(5):
    for dd in range(5):
     v=Vr[a,b,cc,dd]
     if abs(v)<1e-9: continue
     for s1 in (0,1):
      for s2 in (0,1):
        ops=[(2*dd+s2,0),(2*cc+s1,0),(2*b+s2,1),(2*a+s1,1)]
        x=d;sg=1;ok=True
        for p,dag in ops:
            r=a_(p,x,dag)
            if r is None: ok=False;break
            sg*=r[0];x=r[1]
        if ok: H2[di[x],di[d]]+=0.5*v*sg
Sz=np.zeros((10,10));Sp=np.zeros((10,10))
for i in range(5):
    Sz[2*i,2*i]=.5;Sz[2*i+1,2*i+1]=-.5; Sp[2*i,2*i+1]=1  # s=0 up
Szm=onebody(Sz).real;Spm=onebody(Sp).real
S2=Spm.T@Spm+Szm@Szm+Szm  # S-S+ + Sz^2+Sz ; Sp = raises
# check: Sp raises: s=1(down)->s=0(up) ; Sp[up,down]=1 good
eg=[0,3]
def h1(Dq):
    e=np.array([6,-4,-4,6,-4])*Dq
    h=np.zeros((10,10))
    for i in range(5):
        h[2*i,2*i]=h[2*i+1,2*i+1]=e[i]
    return h
U4so=np.zeros((10,10),complex)
for i in range(5):
  for j in range(5):
    for s_ in (0,1): U4so[2*i+s_,2*j+s_]=U4[i,j]
C4m=onebody(np.zeros((10,10)))  # placeholder
# many-body rotation via minors
occ=[[i for i in range(10) if d>>i&1] for d in dets]
C4M=np.zeros((210,210),complex)
for j,oj in enumerate(occ):
  for i,oi in enumerate(occ):
    C4M[i,j]=np.linalg.det(U4so[np.ix_(oi,oj)])
Sz_d=np.diag(Szm)
def levels(Dq):
    H=H2+onebody(h1(Dq)).real
    out=[]
    for S in (0,1,2):
        sel=np.where(abs(Sz_d-S)<1e-9)[0]
        S2s=S2[np.ix_(sel,sel)];w,v=np.linalg.eigh(S2s)
        P=v[:,abs(w-S*(S+1))<1e-6]
        if P.shape[1]==0: continue
        Hs=P.T@H[np.ix_(sel,sel)]@P
        C4s=P.conj().T@C4M[np.ix_(sel,sel)]@P
        e,u=np.linalg.eigh(Hs)
        i=0
        while i<len(e):
            j=i
            while j+1<len(e) and e[j+1]-e[i]<1e-5*B*0+1e-4: j+=1
            sub=u[:,i:j+1];dim=j-i+1
            ch=np.trace(sub.conj().T@C4s@sub).real
            ch=round(ch)
            lab={ (1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}.get((dim,ch),'?%d,%d'%(dim,ch))
            out.append((e[i:j+1].mean(),'%d%s'%(2*S+1,lab)))
            i=j+1
    out.sort();return out
if __name__=="__main__":
    import sys
    for x in np.arange(0,4.01,.5):
        Dq=max(x,1e-3)*B
        L=levels(Dq);e0=L[0][0]
        print(x,[(t,round((e-e0)/B,4)) for e,t in L[:8]])
