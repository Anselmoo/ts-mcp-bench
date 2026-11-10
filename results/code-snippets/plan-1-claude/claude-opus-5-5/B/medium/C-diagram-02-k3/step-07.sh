mkdir -p /tmp/ts && cd /tmp/ts && cat > ts.py <<'EOF'
import math, itertools
from fractions import Fraction
def fac(n): return math.factorial(n)
def w3j(j1,j2,j3,m1,m2,m3):
    if m1+m2+m3!=0: return 0.0
    if abs(m1)>j1 or abs(m2)>j2 or abs(m3)>j3: return 0.0
    t=fac(j1+j2-j3)*fac(j1-j2+j3)*fac(-j1+j2+j3)/fac(j1+j2+j3+1)
    pre=math.sqrt(t*fac(j1+m1)*fac(j1-m1)*fac(j2+m2)*fac(j2-m2)*fac(j3+m3)*fac(j3-m3))
    s=0.0
    for k in range(0,100):
        a=[k, j1+j2-j3-k, j1-m1-k, j2+m2-k, j3-j2+m1+k, j3-j1-m2+k]
        if a[1]<0 or a[2]<0 or a[3]<0: 
            if k>j1+j2+j3: break
            continue
        if a[4]<0 or a[5]<0: continue
        s+=(-1)**k/ (fac(a[0])*fac(a[1])*fac(a[2])*fac(a[3])*fac(a[4])*fac(a[5]))
    return (-1)**(j1-j2-m3)*pre*s
def ck(k,m,mp):
    return (-1)**m*5*w3j(2,k,2,0,0,0)*w3j(2,k,2,-m,m-mp,mp)
B=1.0; C=3902/814
F={0:0.0,2:49*(B+C/7),4:441*(C/35)}
ms=[-2,-1,0,1,2]
# spin orbitals: index i = 2*(m+2)+s, s=0 up,1 down
orbs=[(m,s) for m in ms for s in (0,1)]
def eri(p,q,r,s):  # <pq|rs>, electron1 p->r, electron2 q->s
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=orbs[p],orbs[q],orbs[r],orbs[s]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.0
    return sum(ck(k,m1,m3)*ck(k,m4,m2)*F[k] for k in (0,2,4))
N=10
ERI={}
for p,q,r,s in itertools.product(range(N),repeat=4):
    v=eri(p,q,r,s)
    if abs(v)>1e-14: ERI[(p,q,r,s)]=v
def hcf(Dq):
    h={}
    for i,(m,s) in enumerate(orbs):
        for j,(mp,sp) in enumerate(orbs):
            if s!=sp: continue
            v=0
            if m==mp: v={2:Dq,-2:Dq,1:-4*Dq,-1:-4*Dq,0:6*Dq}[m]
            elif abs(m-mp)==4: v=5*Dq
            if v: h[(i,j)]=v
    return h
dets=[c for c in itertools.combinations(range(N),4)]
def apply_ann(det,i):
    if i not in det: return None,0
    k=det.index(i); return det[:k]+det[k+1:],(-1)**k
def apply_cre(det,i):
    if i in det: return None,0
    l=sorted(det+(i,)); k=l.index(i); return tuple(l),(-1)**k
def Msval(d): return sum(0.5 if orbs[i][1]==0 else -0.5 for i in d)
def Mval(d): return sum(orbs[i][0] for i in d)
# precompute two-body action
def act2(det):
    out={}
    for (p,q,r,s),v in ERI.items():
        d1,f1=apply_ann(det,r)
        if d1 is None: continue
        d2,f2=apply_ann(d1,s)
        if d2 is None: continue
        d3,f3=apply_cre(d2,q)
        if d3 is None: continue
        d4,f4=apply_cre(d3,p)
        if d4 is None: continue
        out[d4]=out.get(d4,0)+0.5*v*f1*f2*f3*f4
    return out
def act1(det,h):
    out={}
    for (p,q),v in h.items():
        d1,f1=apply_ann(det,q)
        if d1 is None: continue
        d2,f2=apply_cre(d1,p)
        if d2 is None: continue
        out[d2]=out.get(d2,0)+v*f1*f2
    return out
def S2act(det):
    # S^2 = S-S+ + Sz^2 + Sz
    out={}
    sz=Msval(det); out[det]=sz*sz+sz
    for a in range(5):
        d1,f1=apply_ann(det,2*a+1); 
        if d1 is None: continue
        d2,f2=apply_cre(d1,2*a)
        if d2 is None: continue
        for b in range(5):
            d3,f3=apply_ann(d2,2*b)
            if d3 is None: continue
            d4,f4=apply_cre(d3,2*b+1)
            if d4 is None: continue
            out[d4]=out.get(d4,0)+f1*f2*f3*f4
    return out
blocks={}
for d in dets:
    if Msval(d)==0: blocks.setdefault(Mval(d)%4,[]).append(d)
V2={d:act2(d) for b in blocks.values() for d in b}
S2={d:S2act(d) for b in blocks.values() for d in b}
def jacobi(A):
    n=len(A); A=[r[:] for r in A]; V=[[float(i==j) for j in range(n)] for i in range(n)]
    for sweep in range(100):
        off=sum(A[i][j]**2 for i in range(n) for j in range(i+1,n))
        if off<1e-26: break
        for p in range(n):
            for q in range(p+1,n):
                if abs(A[p][q])<1e-30: continue
                th=(A[q][q]-A[p][p])/(2*A[p][q])
                t=(1 if th>=0 else -1)/(abs(th)+math.sqrt(th*th+1))
                c=1/math.sqrt(t*t+1); s=t*c
                for k in range(n):
                    akp,akq=A[k][p],A[k][q]
                    A[k][p]=c*akp-s*akq; A[k][q]=s*akp+c*akq
                for k in range(n):
                    apk,aqk=A[p][k],A[q][k]
                    A[p][k]=c*apk-s*aqk; A[q][k]=s*apk+c*aqk
                for k in range(n):
                    vkp,vkq=V[k][p],V[k][q]
                    V[k][p]=c*vkp-s*vkq; V[k][q]=s*vkp+c*vkq
    return [A[i][i] for i in range(n)],V
def solve(Dq):
    h=hcf(Dq); res=[]
    for mod,b in blocks.items():
        idx={d:i for i,d in enumerate(b)}; n=len(b)
        H=[[0.0]*n for _ in range(n)]; S=[[0.0]*n for _ in range(n)]
        for d in b:
            for o,dic in ((H,V2[d]),(H,act1(d,h)),(S,S2[d])):
                for d2,v in dic.items(): o[idx[d2]][idx[d]]+=v
        w,V=jacobi(H)
        for k in range(n):
            vec=[V[i][k] for i in range(n)]
            s2=sum(vec[i]*S[i][j]*vec[j] for i in range(n) for j in range(n))
            Sv=round((-1+math.sqrt(1+4*s2))/2)
            res.append((w[k],Sv,mod))
    res.sort()
    # group
    levels=[]; 
    for e,S,mod in res:
        for L in levels:
            if L['S']==S and abs(L['e']-e)<1e-7: L['mods'].append(mod); break
        else: levels.append({'e':e,'S':S,'mods':[mod]})
    pat={(0,):'A1',(2,):'A2',(0,2):'E',(0,1,3):'T1',(1,2,3):'T2'}
    out=[]
    for L in levels:
        key=tuple(sorted(L['mods']))
        out.append((L['e'],2*L['S']+1,pat.get(key,str(key))))
    return out
EOF
echo ok