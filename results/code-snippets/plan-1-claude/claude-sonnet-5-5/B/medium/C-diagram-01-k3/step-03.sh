cat > a.py <<'E'
import numpy as np, itertools, json
from sympy.physics.wigner import wigner_3j
B=828.;C=3390.
F4=63*C/5;F2=(441*B+5*F4)/9;F={2:F2,4:F4}
ms=range(-2,3)
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k:return 0.
    return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,q,mp))
cc={(k,m,mp):ck(k,m,mp) for k in(2,4) for m in ms for mp in ms}
so=[(m,s) for m in ms for s in(0,1)]
def g(a,b,c,d):
    if a[1]!=c[1] or b[1]!=d[1] or a[0]+b[0]!=c[0]+d[0]:return 0.
    return sum(cc[(k,a[0],c[0])]*cc[(k,d[0],b[0])]*F[k] for k in(2,4))
dets=list(itertools.combinations(range(10),3));idx={d:i for i,d in enumerate(dets)}
def sortsign(l):
    inv=sum(1 for a in range(len(l)) for b in range(a+1,len(l)) if l[a]>l[b])
    return tuple(sorted(l)),(-1)**inv
def two(p,q,r,s,det):
    l=list(det);sg=1
    for o in (r,s):
        if o not in l:return None
        i=l.index(o);sg*=(-1)**i;l.pop(i)
    for o in (q,p):
        if o in l:return None
        l.insert(0,o)
    t,s2=sortsign(l);return t,sg*s2
G={}
for p in range(10):
 for q in range(10):
  for r in range(10):
   for s in range(10):
    if p!=q and r!=s:
     x=g(so[p],so[q],so[r],so[s])
     if abs(x)>1e-12:G[(p,q,r,s)]=x
H2=np.zeros((120,120))
for d in dets:
    for (p,q,r,s),x in G.items():
        res=two(p,q,r,s,d)
        if res:H2[idx[res[0]],idx[d]]+=0.5*x*res[1]
V={2:1,-2:1,1:-4,-1:-4,0:6}
H1=np.zeros((120,120))
for d in dets:
    i=idx[d]
    for pos,o in enumerate(d):
        H1[i,i]+=V[so[o][0]]
        m,s=so[o]
        if abs(m)==2:
            n=so.index((-m,s))
            if n not in d:
                arr=list(d);arr[pos]=n;t,sg=sortsign(arr)
                H1[idx[t],i]+=5*sg
U=np.diag([np.exp(-1j*m*np.pi/2) for m,s in so])
Cm=np.zeros((120,120),complex)
for d in dets:
    for e in dets:
        Cm[idx[e],idx[d]]=np.linalg.det(U[np.ix_(e,d)])
sz=np.array([sum(1 if so[o][1]==0 else -1 for o in d)/2 for d in dets])
def lab(S,n,ch):
    return {(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}[(n,ch)]
def levels(Dq):
    H=H2+Dq*H1; levs=[]
    qs=[]
    for s_ in (1.5,0.5):
        ix=np.where(sz==s_)[0];h=H[np.ix_(ix,ix)];c=Cm[np.ix_(ix,ix)]
        w,v=np.linalg.eigh(h);i=0;cur=[]
        while i<len(w):
            j=i
            while j+1<len(w) and abs(w[j+1]-w[i])<1e-4:j+=1
            sub=v[:,i:j+1];n=j-i+1
            ch=int(round(np.trace(sub.conj().T@c@sub).real))
            cur.append((w[i],n,ch));i=j+1
        if s_==1.5:
            qs=cur
            for w_,n,ch in cur:levs.append((w_,'4'+lab(0,n,ch)))
        else:
            for w_,n,ch in cur:
                if any(abs(w_-x[0])<1e-3 and n==x[1] for x in qs):continue
                levs.append((w_,'2'+lab(0,n,ch)))
    levs.sort(key=lambda t:(round(t[0],3),t[1]))
    return [(round((e-levs[0][0])/B,4),t) for e,t in levs]
pts=[];grid=np.arange(0,4.01,.5)
for x in grid:
    L=levels(max(x,1e-5)*B)
    print(x,L[:8]);pts.append((x,L[:6]))
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
xs=np.linspace(0.02,4,80)
data=[levels(x*B)[:10] for x in xs]
for k in range(10):plt.plot(xs,[d[k][0] for d in data],'.',ms=2)
plt.xlabel('Dq/B');plt.ylabel('E/B');plt.savefig('diagram.png',dpi=120)
E
python3 a.py; sha256sum diagram.png; pwd