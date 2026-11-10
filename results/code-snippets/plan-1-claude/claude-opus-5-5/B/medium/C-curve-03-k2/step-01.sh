
pip list 2>/dev/null | grep -i -E "sympy|numpy"
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from functools import lru_cache
B=784.;C=3699.
# F0 arbitrary 0, F2=49B+7C? Racah: B=F2-5F4, C=35F4 with F2=F^2/49,F4=F^4/441
F4=C/35; F2=B+5*F4
Fk={0:0.0,2:F2*49,4:F4*441}
ms=[-2,-1,0,1,2]
@lru_cache(None)
def ck(k,l1,m1,l2,m2):
    # c^k(lm1,lm2) = sqrt(4pi/(2k+1)) * int Y*_{l m1} Y_{k,m1-m2} Y_{l m2}
    q=m1-m2
    if abs(q)>k: return 0.0
    # int Y*_{2m1} Y_{kq} Y_{2m2} = (-1)^m1 gaunt(2,k,2,-m1,q,m2)
    return float((-1)**m1*gaunt(2,k,2,-m1,q,m2))*np.sqrt(4*np.pi/(2*k+1))
def R(a,b,c,d): # <ab|1/r|cd>, spin-orbitals (m,s)
    if a[1]!=c[1] or b[1]!=d[1]: return 0.0
    if a[0]+b[0]!=c[0]+d[0]: return 0.0
    return sum(ck(k,2,a[0],2,c[0])*ck(k,2,d[0],2,b[0])*Fk[k] for k in (0,2,4))
so=[(m,s) for m in ms for s in (1,-1)]
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
# two-electron operator via second quantization
def apply2(det,p,q,r,s):
    # a_p^+ a_q^+ a_s a_r |det>
    occ=list(det);sign=1
    for o in (r,s):
        if o not in occ: return None
        i=occ.index(o);sign*=(-1)**i;occ.pop(i)
    for o in (q,p):
        if o in occ: return None
        # insert at front: count ordering
        occ.insert(0,o)
    # sort with sign
    perm=sorted(range(len(occ)),key=lambda i:occ[i])
    arr=occ[:]
    # parity
    p_=list(np.argsort(arr));par=1;vis=[False]*len(p_)
    for i in range(len(p_)):
        if not vis[i]:
            j=i;l=0
            while not vis[j]: vis[j]=True;j=p_[j];l+=1
            par*=(-1)**(l-1)
    return tuple(sorted(arr)),sign*par
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
    res=apply2(d,p,q,r,s)
    if res: Hee[idx[res[0]],j]+=0.5*v*res[1]
# crystal field in Ylm: Oh: V = Dq*(6 for m=0 ... ) use matrix: <0|V|0>=6Dq,<±1|=-4Dq,<±2|=Dq, <2|V|-2>=5Dq
def cf1(m1,m2):
    if m1==m2: return {0:6,1:-4,-1:-4,2:1,-2:1}[m1]
    if abs(m1-m2)==4: return 5
    return 0
Hcf=np.zeros((N,N))
for j,d in enumerate(dets):
  for p in range(10):
    for r in range(10):
      if so[p][1]!=so[r][1]: continue
      v=cf1(so[p][0],so[r][0])
      if v==0: continue
      occ=list(d)
      if r not in occ: continue
      i=occ.index(r);sg=(-1)**i;occ.pop(i)
      if p in occ: continue
      occ.insert(0,p); arr=occ
      srt=sorted(arr); par=1
      for a in range(len(arr)):
        for b in range(a+1,len(arr)):
          if arr[a]>arr[b]: par=-par
      Hcf[idx[tuple(srt)],j]+=v*sg*par
# S^2
Sz=np.diag([sum(so[o][1] for o in d)/2 for d in dets])
Sp=np.zeros((N,N))
for j,d in enumerate(dets):
  for m in ms:
    p=so.index((m,1));r=so.index((m,-1))
    occ=list(d)
    if r not in occ or p in occ: continue
    i=occ.index(r);sg=(-1)**i;occ.pop(i);occ.insert(0,p);arr=occ
    par=1
    for a in range(len(arr)):
      for b in range(a+1,len(arr)):
        if arr[a]>arr[b]: par=-par
    Sp[idx[tuple(sorted(arr))],j]+=sg*par
S2=Sp.T@Sp+Sz@Sz+Sz
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
    lab={1:{1:'A1',-1:'A2'},2:{0:'E'},3:{1:'T1',-1:'T2'}}[dim].get(int(round(ch)),'?')
    out.append((w[i],f"{mult}{lab}"))
    i=j
  g=out[0][0]
  print(x,[(l,round(e-g,3)) for e,l in out[:5]])
for x in (1.45,2.45,3.0,2.0,2.2): run(x)
EOF
python3 /tmp/d7.py
