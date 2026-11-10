python3 - <<'EOF'
import numpy as np
from scipy.special import lpmv, factorial
from scipy.optimize import least_squares
xg,wg=np.polynomial.legendre.leggauss(30)
phis=np.linspace(0,2*np.pi,60,endpoint=False); wp=2*np.pi/60
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij'); W=(wg[:,None]*wp*np.ones_like(TH))
def Y(l,m,th,ph):
    am=abs(m); N=np.sqrt((2*l+1)/(4*np.pi)*factorial(l-am)/factorial(l+am))
    y=N*lpmv(am,l,np.cos(th))*np.exp(1j*am*ph)
    if m<0: y=(-1)**am*np.conj(y)
    return y
ms=[-2,-1,0,1,2]
Yd={m:Y(2,m,TH,PH) for m in ms}
Ang={}
for k in (2,4):
    for a in ms:
        for c in ms:
            for q in range(-k,k+1):
                Ang[(a,c,k,q)]=np.sum(W*np.conj(Yd[a])*Yd[c]*np.conj(Y(k,q,TH,PH)))
so=[(m,s) for m in ms for s in (0,1)]
states=[x for x in range(1024) if bin(x).count('1')==8]
idx={x:i for i,x in enumerate(states)}; D=len(states)
def op(ops):
    M=np.zeros((D,D))
    for x in states:
        y=x; s=1; ok=True
        for typ,i in reversed(ops):
            nb=bin(y&((1<<i)-1)).count('1')
            if typ=='c':
                if not (y>>i)&1: ok=False;break
                y^=(1<<i); s*=(-1)**nb
            else:
                if (y>>i)&1: ok=False;break
                y|=(1<<i); s*=(-1)**nb
        if ok and y in idx: M[idx[y],idx[x]]+=s
    return M
Sp=sum(op([('a',2*m),('c',2*m+1)]) for m in range(5))
Sz=sum(0.5*(op([('a',2*m),('c',2*m)])-op([('a',2*m+1),('c',2*m+1)])) for m in range(5))
S2=Sp.T@Sp+Sz@Sz+Sz
Mops=[]
for a in range(10):
 for b in range(10):
  for c in range(10):
   for d in range(10):
    ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
    if sa!=sc or sb!=sd or a==b or c==d: continue
    coef=[]
    for k in (2,4):
        s=sum(Ang[(ma,mc,k,q)]*Ang[(mb,md,k,-q)]*(-1)**q for q in range(-k,k+1))
        coef.append(4*np.pi/(2*k+1)*s)
    if max(abs(x) for x in coef)<1e-12: continue
    Mops.append((np.array(coef),op([('a',a),('a',b),('c',d),('c',c)])))
H2=sum(0.5*c[0]*M for c,M in Mops); H4=sum(0.5*c[1]*M for c,M in Mops)
one={}
for i in range(10):
  for j in range(10):
    if so[i][1]==so[j][1]: one[(i,j)]=op([('a',i),('c',j)])
s2=np.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
eg=[vec({0:1}),vec({2:1/s2,-2:1/s2})]
t2=[vec({1:-1/s2,-1:1/s2}),vec({1:-1j/s2,-1:-1j/s2}),vec({2:-1j/s2,-2:1j/s2})]
def Hcf(Dq):
    P=sum(6*Dq*np.outer(v,v.conj()) for v in eg)+sum(-4*Dq*np.outer(v,v.conj()) for v in t2)
    H=np.zeros((D,D),complex)
    for (i,j),M in one.items():
        if abs(P[so[i][0]+2,so[j][0]+2])>1e-14: H+=P[so[i][0]+2,so[j][0]+2]*M
    return H
Pen=1e6*(S2-2*np.eye(D))@(S2-2*np.eye(D))
Pens=1e6*S2@S2
def spec(Dq,B,C):
    F2=49*B+7*C; F4=441*C/35
    H=Hcf(Dq)+F2*H2+F4*H4
    wt,vt=np.linalg.eigh(H+Pen)
    ws,vs=np.linalg.eigh(H+Pens)
    wt=wt[wt<5e5]; ws=ws[ws<5e5]
    return wt,ws
def classes(wt,ws):
    # group degenerate levels
    def group(w):
        g=[]
        for x in w:
            if g and abs(x-g[-1][0])<0.5: g[-1][1]+=1
            else: g.append([x,1])
        return g
    return group(wt),group(ws)
# quick check
wt,ws=spec(977,1000,4000)
gt,gs=classes(wt,ws)
print('triplet groups',[(round(x,0),n) for x,n in gt])
print('singlet groups',[(round(x,0),n) for x,n in gs])
np.save if False else None
import pickle,sys
sys.stdout.flush()
def resid(p):
    Dq,B,C=p
    wt,ws=spec(Dq,B,C)
    gt,gs=classes(wt,ws)
    t=[x for x,n in gt if n==9]  # 3T2, 3T1F, 3T1P (in order)
    s=[x for x,n in gs if n==2]
    g0=gt[0][0]
    t=[x-g0 for x in t]; s=[x-g0 for x in s]
    model=[t[0],t[1],t[2],s[0]]
    return np.array(model)-np.array([9770,16050,26740,12987])
sol=least_squares(resid,[977,900,4000],x_scale=[100,100,500])
print('fit',sol.x,resid(sol.x),'Dq',sol.x[0])
wt,ws=spec(*sol.x); gt,gs=classes(wt,ws)
print('triplet groups',[(round(x-gt[0][0],0),n) for x,n in gt])
print('singlet groups',[(round(x-gt[0][0],0),n) for x,n in gs])
EOF