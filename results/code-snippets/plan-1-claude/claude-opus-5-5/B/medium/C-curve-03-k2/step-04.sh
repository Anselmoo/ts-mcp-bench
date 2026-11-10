cd /tmp/tsbench-run-yxvn6zk7; cat << 'EOF' > d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from functools import lru_cache
B=784.;C=3699.
F4=C/35; F2=B+5*F4
Fk={0:0.0,2:F2*49,4:F4*441}
ms=[-2,-1,0,1,2]
@lru_cache(None)
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*gaunt(2,k,2,-m1,q,m2))*np.sqrt(4*np.pi/(2*k+1))
def R(a,b,c,d):
    if a[1]!=c[1] or b[1]!=d[1]: return 0.0
    if a[0]+b[0]!=c[0]+d[0]: return 0.0
    return sum(ck(k,a[0],c[0])*ck(k,d[0],b[0])*Fk[k] for k in (0,2,4))
so=[(m,s) for m in ms for s in (1,-1)]
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def parity(arr):
    par=1
    for a in range(len(arr)):
        for b in range(a+1,len(arr)):
            if arr[a]>arr[b]: par=-par
    return par
def ann_cre(det,cre,ann):
    occ=list(det);sign=1
    for o in ann:
        if o not in occ: return None
        i=occ.index(o);sign*=(-1)**i;occ.pop(i)
    for o in cre:
        if o in occ: return None
        occ.insert(0,o)
    return tuple(sorted(occ)),sign*parity(occ)
Hee=np.zeros((N,N))
V={}
for p in range(10):
  for q in range(10):
    for r in range(10):
      for s in range(10):
        v=R(so[p],so[q],so[r],so[s])
        if abs(v)>1e-12: V[(p,q,r,s)]=v
for j,d in enumerate(dets):
  for (p,q,r,s),v in V.items():
    res=ann_cre(d,(q,p),(r,s))   # a_p+ a_q+ a_s a_r : apply a_r first? a_s a_r|> : a_r first
    if res: Hee[idx[res[0]],j]+=0.5*v*res[1]
def cf1(m1,m2):
    if m1==m2: return {0:6,1:-4,-1:-4,2:1,-2:1}[m1]
    if abs(m1-m2)==4: return 5
    return 0
Hcf=np.zeros((N,N));Sp=np.zeros((N,N))
for j,d in enumerate(dets):
  for p in range(10):
    for r in range(10):
      if so[p][1]!=so[r][1]: continue
      v=cf1(so[p][0],so[r][0])
      if v==0: continue
      res=ann_cre(d,(p,),(r,))
      if res: Hcf[idx[res[0]],j]+=v*res[1]
  for m in ms:
      res=ann_cre(d,(so.index((m,1)),),(so.index((m,-1)),))
      if res: Sp[idx[res[0]],j]+=res[1]
print("herm",abs(Hee-Hee.T).max(),abs(Hcf-Hcf.T).max())
Sz=np.diag([sum(so[o][1] for o in d)/2 for d in dets])
S2=Sp.T@Sp+Sz@Sz-Sz
C4=np.diag([np.exp(1j*np.pi/2*sum(so[o][0] for o in d)) for d in dets])
def run(x):
  H=Hee+x*B*Hcf
  w,U=np.linalg.eigh(H)
  w=w/B
  out=[];i=0
  while i<N:
    j=i
    while j<N and abs(w[j]-w[i])<1e-6: j+=1
    P=U[:,i:j]
    s2=np.trace(P.T@S2@P).real/(j-i); S=(-1+np.sqrt(1+4*s2))/2
    mult=int(round(2*S+1)); dim=(j-i)//mult
    ch=np.trace(P.conj().T@C4@P).real/mult
    lab={1:{1:'A1',-1:'A2'},2:{0:'E'},3:{1:'T1',-1:'T2'}}.get(dim,{}).get(int(round(ch)),'?%d,%d'%(dim,round(ch)))
    out.append((w[i],f"{mult}{lab}"))
    i=j
  g=out[0][0]
  print(x,[(l,round(e-g,3)) for e,l in out[:6]])
run(0)
for x in (1.45,2.45,3.0,2.0,2.2): run(x)
EOF
python3 d7.py