import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ml=[-2,-1,0,1,2]
orbs=[(m,s) for m in ml for s in (0,1)]
cc={}
for k in (0,2,4):
  for a in ml:
    for b in ml:
      cc[k,a,b]=float((-1)**(-a)*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-a,a-b,b))
idx={m:i for i,m in enumerate(ml)}
Hcf=np.zeros((5,5))
Hcf[idx[0],idx[0]]=6; Hcf[idx[1],idx[1]]=Hcf[idx[-1],idx[-1]]=-4
Hcf[idx[2],idx[2]]=Hcf[idx[-2],idx[-2]]=1
Hcf[idx[2],idx[-2]]=Hcf[idx[-2],idx[2]]=5
def sz(st): return sum(0.5 if orbs[o][1]==0 else -0.5 for o in st)
allst=list(itertools.combinations(range(10),7))
def mats(M):
  states=[s for s in allst if abs(sz(s)-M)<1e-9]
  sidx={s:i for i,s in enumerate(states)}; N=len(states)
  H1=np.zeros((N,N)); Hk={2:np.zeros((N,N)),4:np.zeros((N,N))}
  def ann(lst,o):
    p=lst.index(o); return (-1)**p, lst[:p]+lst[p+1:]
  def cre(lst,o):
    p=sum(1 for x in lst if x<o); return (-1)**p, sorted(lst+[o])
  for a,st in enumerate(states):
    occ=list(st)
    for i in occ:
      for j in range(10):
        if orbs[j][1]!=orbs[i][1]: continue
        h=Hcf[idx[orbs[j][0]],idx[orbs[i][0]]]
        if h==0 or (j!=i and j in occ): continue
        s1,L=ann(occ,i); s2,L=cre(L,j)
        H1[sidx[tuple(L)],a]+=s1*s2*h
    for i,j in itertools.combinations(occ,2):
      rest=[x for x in occ if x not in (i,j)]
      for k,l in itertools.combinations(range(10),2):
        if k in rest or l in rest: continue
        (mi,si),(mj,sj),(mk,sk),(mm,sl)=orbs[i],orbs[j],orbs[k],orbs[l]
        if mi+mj!=mk+mm: continue
        if sk+sl!=si+sj: continue
        s1,L=ann(occ,i); s2,L=ann(L,j); s3,L=cre(L,l); s4,L=cre(L,k)
        sg=s1*s2*s3*s4
        for kk in (2,4):
          v=0
          if sk==si and sl==sj: v+=cc[kk,mk,mi]*cc[kk,mj,mm]
          if sl==si and sk==sj: v-=cc[kk,mm,mi]*cc[kk,mj,mk]
          Hk[kk][sidx[tuple(L)],a]+=sg*v
  return H1,Hk
A=mats(1.5); Bm=mats(0.5)
np.save('/dev/shm/w/x.npy',np.array([0]))
def eig(m,Dq,B,C):
  H1,Hk=m; F2=49*B+7*C; F4=441*C/35
  return np.linalg.eigvalsh(Dq*H1+F2*Hk[2]+F4*Hk[4])
def groups(w):
  out=[];i=0
  while i<len(w):
    j=i
    while j<len(w) and abs(w[j]-w[i])<1e-4: j+=1
    out.append((w[i],j-i)); i=j
  return out
def levels(Dq,B,C):
  q=groups(eig(A,Dq,B,C)); h=groups(eig(Bm,Dq,B,C))
  d=[]
  for e,n in h:
    nq=sum(g for E,g in q if abs(E-e)<1e-4)
    if n-nq>0: d.append((e,n-nq))
  g=q[0][0]
  return [(round(e-g,1),n) for e,n in q],[(round(e-g,1),n) for e,n in d]
q,d=levels(0,1000,4000);print(q,d)
q,d=levels(625,800,3200)
print(q);print(d)
