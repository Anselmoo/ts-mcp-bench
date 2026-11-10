
cat > <SANDBOX_TMP>/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=800.;C=3473.
F4=63*C/5;F2=(441*B+5*F4)/9
F={2:F2,4:F4}
l=2
def ck(k,m1,m2):
    q=m1-m2
    return float((-1)**m1*(2*l+1)*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m1,q,m2))
ms=[-2,-1,0,1,2]
def Vv(a,b,c,d):
    if a+b!=c+d: return 0
    q=a-c;s=0
    for k in (2,4):
        s+=F[k]*(-1)**q*ck(k,a,c)*ck(k,d,b)
    return s
spo=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),5))
idx={x:i for i,x in enumerate(dets)}
n=len(dets)
def apply(ops,det):
    det=list(det);sg=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in det:return None
            p=det.index(o);sg*=(-1)**p;det.pop(p)
        else:
            if o in det:return None
            p=sum(1 for x in det if x<o);sg*=(-1)**p;det.insert(p,o)
    return sg,tuple(det)
# precompute two-electron
V2=[]
for p in range(10):
 for q in range(10):
  for r in range(10):
   for s in range(10):
    a,sa=spo[p];b,sb=spo[q];c,sc=spo[r];d,sd=spo[s]
    if sa==sc and sb==sd:
        x=Vv(a,b,c,d)
        if abs(x)>1e-9:V2.append((p,q,r,s,x))
Hee=np.zeros((n,n))
for j,det in enumerate(dets):
    for p,q,r,s,x in V2:
        t=apply([('c',p),('c',q),('a',s),('a',r)],det)
        if t:Hee[idx[t[1]],j]+=0.5*x*t[0]
H1=[np.zeros((n,n)) for _ in range(1)][0]
# one-electron unit Dq matrix
d={0:6,1:-4,-1:-4,2:1,-2:1}
h=np.zeros((5,5))
for m in ms:h[m+2,m+2]=d[m]
h[0,4]=h[4,0]=5
for j,det in enumerate(dets):
    for p in range(10):
        for q in range(10):
            if spo[p][1]!=spo[q][1]:continue
            x=h[spo[p][0]+2,spo[q][0]+2]
            if x==0:continue
            t=apply([('c',p),('a',q)],det)
            if t:H1[idx[t[1]],j]+=x*t[0]
Sm=np.zeros((n,n))
for j,det in enumerate(dets):
    for i in det:
        if spo[i][1]==0:
            t=apply([('c',i+1),('a',i)],det)
            if t:Sm[idx[t[1]],j]+=t[0]
Sz=np.diag([sum(.5 if spo[i][1]==0 else -.5 for i in det) for det in dets])
S2=Sm.T@Sm+Sz@Sz+Sz
for x in (1.45,2.55,3.25):
    H=Hee+x*B*H1
    w,v=np.linalg.eigh(H+1e-3*S2)
    s2=np.array([v[:,i]@S2@v[:,i] for i in range(n)])
    w=np.array([v[:,i]@H@v[:,i] for i in range(n)])
    lv=[];i=0
    while i<n:
        j=i
        while j<n and abs(w[j]-w[i])<1e-2*B:j+=1
        lv.append(((w[i]-w[0])/B,j-i,round(s2[i],2)));i=j
    print(x,lv[:7])
E
python3 <SANDBOX_TMP>/a.py
