import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=800.;C=3473.
F4=C/35;F2=B+5*F4
Fk={0:0.0,2:F2*49,4:F4*441}
ms=[-2,-1,0,1,2]
def ck(k,m,mp): return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),5)); idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def g(a,b,c,d):
  (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[a],so[b],so[c],so[d]
  if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0
  return sum(ck(k,m1,m3)*ck(k,m4,m2)*Fk[k] for k in (2,4))
G=np.zeros((10,)*4)
for a,b,c,d in itertools.product(range(10),repeat=4): G[a,b,c,d]=g(a,b,c,d)
def apply2(det,a,b,c,d):
  st=list(det);sg=1
  for op in (c,d):
    if op not in st: return None
    p=st.index(op); sg*= (-1)**p; st.pop(p)
  for op in (b,a):
    if op in st: return None
    p=sum(1 for x in st if x<op); sg*=(-1)**p; st.insert(p,op)
  return tuple(st),sg
H2=np.zeros((N,N))
for i,dt in enumerate(dets):
  for a,b,c,d in itertools.product(range(10),repeat=4):
    v=G[a,b,c,d]
    if v==0: continue
    r=apply2(dt,a,b,c,d)
    if r: H2[idx[r[0]],i]+=0.5*v*r[1]
def one(mat):
  M=np.zeros((N,N))
  for i,dt in enumerate(dets):
    for a in range(10):
      for c in range(10):
        if so[a][1]!=so[c][1]: continue
        v=mat[ms.index(so[a][0]),ms.index(so[c][0])]
        if v==0: continue
        st=list(dt)
        if c not in st: continue
        p=st.index(c);sg=(-1)**p;st.pop(p)
        if a in st: continue
        q=sum(1 for x in st if x<a);sg*=(-1)**q;st.insert(q,a)
        M[idx[tuple(st)],i]+=v*sg
  return M
V=np.diag([1.,-4,6,-4,1]);V[0,4]=V[4,0]=5
HV=one(V)
Sz=np.array([sum(0.5 if so[x][1] else -0.5 for x in dt) for dt in dets])
Sp=np.zeros((N,N))
for i,dt in enumerate(dets):
  for x in dt:
    if so[x][1]==0 and x+1 not in dt:
      st=list(dt);p=st.index(x);sg=(-1)**p;st.pop(p);q=sum(1 for y in st if y<x+1);sg*=(-1)**q;st.insert(q,x+1)
      Sp[idx[tuple(st)],i]+=sg
S2=Sp.T@Sp+np.diag(Sz**2+Sz)
C4=np.diag([np.prod([np.exp(1j*np.pi/2*so[x][0]) for x in dt]) for dt in dets])
print("sym",np.abs(H2-H2.T).max())
for dqb in (0,1.45,2.55,3.25):
  H=H2+dqb*B*HV+1e-4*S2
  w,U=np.linalg.eigh(H)
  grp=[];i=0
  while i<N:
    j=i
    while j<N and w[j]-w[i]<0.05: j+=1
    grp.append((i,j));i=j
  E0=w[0];out=[]
  for i,j in grp[:7]:
    Us=U[:,i:j];s2=np.real(np.trace(Us.T@S2@Us))/(j-i)
    S=(-1+np.sqrt(1+4*s2))/2;mult=int(round(2*S+1));deg=(j-i)//mult
    ch=np.real(np.trace(Us.conj().T@C4@Us))/mult
    lab={1:{1:'A1',-1:'A2'},2:{0:'E'},3:{1:'T1',-1:'T2'}}.get(deg,{}).get(int(round(ch)),f'?{deg},{ch:.2f}')
    out.append((f"{mult}{lab}",round((w[i]-E0)/B,3)))
  print(dqb,out)
