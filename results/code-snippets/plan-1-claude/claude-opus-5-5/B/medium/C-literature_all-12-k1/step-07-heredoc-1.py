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
  c4=np.array([np.exp(0.5j*np.pi*sum(orbs[o][0] for o in s)) for s in states])
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
  return H1,Hk,c4
A=mats(1.5); Bm=mats(0.5)
def lev(m,Dq,B,C):
  H1,Hk,c4=m; F2=49*B+7*C; F4=441*C/35
  w,v=np.linalg.eigh(Dq*H1+F2*Hk[2]+F4*Hk[4])
  out=[];i=0
  while i<len(w):
    j=i
    while j<len(w) and abs(w[j]-w[i])<1e-4: j+=1
    ch=np.real(np.sum(np.abs(v[:,i:j])**2*c4[:,None]))
    n=j-i
    out.append([w[i],n,round(ch)]); i=j
  return out
def name(n,ch):
  return {(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}.get((n,ch),'?%d%d'%(n,ch))
def levels(Dq,B,C):
  q=lev(A,Dq,B,C); h=lev(Bm,Dq,B,C)
  g=q[0][0]
  Q=[(e-g,name(n,ch)) for e,n,ch in q]
  D=[]
  for e,n,ch in h:
    m=[x for x in q if abs(x[0]-e)<1e-4]
    if m:
      n-=m[0][1]; ch-=m[0][2]
    if n>0: D.append((e-g,name(n,ch)))
  return Q,D
def pred(p):
  Q,D=levels(*p)
  def get(L,lab,k): return [e for e,l in L if l==lab][k]
  return np.array([get(Q,'T2',0),get(Q,'A2',0),get(Q,'T1',1),get(D,'T1',1)])
obs=np.array([6150,12400,16850,19000])
r=least_squares(lambda p:pred(p)-obs,[625,800,3200])
print(r.x, pred(r.x), pred(r.x)-obs)
Q,D=levels(*r.x); print([(round(e),l) for e,l in Q]); print([(round(e),l) for e,l in D][:10])
# quartet-only fit
r2=least_squares(lambda p:pred([p[0],p[1],r.x[2]])[:3]-obs[:3],[625,800]); print(r2.x)
