mkdir -p /tmp/w && cd /tmp/w && cat > t.py <<'E'
import numpy as np, itertools, json
from sympy.physics.wigner import gaunt
from math import factorial
B=814.;C=3902.
F2=49*(1+C/B/7);F4=441*(C/B/35)  # in units of B
Fk={0:0,2:F2,4:F4}
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # <l m1|C^k|l m2>
    return float((-1)**m1*5*gaunt(2,k,2,-m1,m1-m2,m2)*gaunt(2,0,2,0,0,0)*0+ (-1)**m1*5*gaunt(2,k,2,0,0,0)*0) if False else float((-1)**m1*5*__import__('sympy.physics.wigner',fromlist=['x']).wigner_3j(2,k,2,-m1,m1-m2,m2)*__import__('sympy.physics.wigner',fromlist=['x']).wigner_3j(2,k,2,0,0,0))
# <m1 m2|g|m3 m4> = sum_k F^k/(...) c^k(m1,m3) c^k(m4,m2)  (CS F^k = Fk_slater/..)
cc={k:np.array([[ck(k,a,b) for b in ms] for a in ms]) for k in (2,4)}
G=np.zeros((5,5,5,5))
for a in range(5):
 for b in range(5):
  for c in range(5):
   for d in range(5):
    if ms[a]+ms[b]!=ms[c]+ms[d]: continue
    G[a,b,c,d]=sum(Fk[k]/ (49 if k==2 else 441)*0+ (Fk[k]/(49 if k==2 else 441))*cc[k][a,c]*cc[k][d,b] for k in (2,4))
# note: with F^k_CS=F/49,F/441 above gives CS values: F2cs=B+C/7 etc (units B)
# orbitals: real basis -> complex
def real_in_complex():
    s=1/np.sqrt(2)
    v={}
    def vec(d):
        x=np.zeros(5,complex)
        for m,c in d.items(): x[m+2]=c
        return x
    z2=vec({0:1}); x2y2=vec({2:s,-2:s}); xy=vec({2:-1j*s,-2:1j*s})
    xz=vec({1:s,-1:-s}); yz=vec({1:1j*s,-1:1j*s})
    return [z2,x2y2],[xy,xz,yz]
eg,t2=real_in_complex()
def hcf(Dq):
    h=np.zeros((5,5),complex)
    for v in eg: h+=6*Dq*np.outer(v,v.conj())
    for v in t2: h+=-4*Dq*np.outer(v,v.conj())
    return h
# spin orbitals index: orb*2+spin
so=[(m,s) for m in range(5) for s in (0,1)]
def dets(nu,nd):
    out=[]
    for u in itertools.combinations(range(5),nu):
        for d in itertools.combinations(range(5),nd):
            out.append(tuple(sorted([2*i for i in u]+[2*i+1 for i in d])))
    return out
def build(Dq,nu,nd):
    D=dets(nu,nd);idx={d:i for i,d in enumerate(D)};N=len(D)
    H=np.zeros((N,N),complex);S2=np.zeros((N,N));C4=np.zeros(N,complex)
    h=hcf(Dq)
    def apply_ops(d,ops):
        # ops list of (create?,so) applied right to left; returns (det,sign) or None
        l=list(d);sign=1
        for cr,p in reversed(ops):
            if cr:
                if p in l:return None
                pos=sum(1 for x in l if x<p);sign*=(-1)**pos;l.insert(pos,p)
            else:
                if p not in l:return None
                pos=l.index(p);sign*=(-1)**pos;l.pop(pos)
        return tuple(l),sign
    for j,d in enumerate(D):
        C4[j]=np.exp(-1j*np.pi/2*sum(ms[p//2] for p in d))
        for a in range(5):
          for b in range(5):
            if abs(h[a,b])<1e-14:continue
            for s in (0,1):
              r=apply_ops(d,[(1,2*a+s),(0,2*b+s)])
              if r: H[idx[r[0]],j]+=r[1]*h[a,b]
        for a in range(5):
         for b in range(5):
          for c in range(5):
           for e in range(5):
            g=G[a,b,c,e]
            if g==0:continue
            for s in (0,1):
             for t in (0,1):
              r=apply_ops(d,[(1,2*a+s),(1,2*b+t),(0,2*e+t),(0,2*c+s)])
              if r: H[idx[r[0]],j]+=0.5*g*r[1]*1
    # S2 = S-S+ + Sz(Sz+1)
    Sz=(nu-nd)/2
    for j,d in enumerate(D):
        # S-S+ : sum_{ab} a†_{a dn} a_{a up} a†_{b up} a_{b dn}
        for a in range(5):
         for b in range(5):
          r=apply_ops(d,[(1,2*a+1),(0,2*a),(1,2*b),(0,2*b+1)])
          if r: S2[idx[r[0]],j]+=r[1]
        S2[j,j]+=Sz*(Sz+1)
    return H,S2,C4,D
def levels(Dq):
    res=[]
    for S,(nu,nd) in {2:(4,0),1:(3,1),0:(2,2)}.items():
        H,S2,C4,D=build(Dq,nu,nd)
        assert np.allclose(H,H.conj().T)
        M=H+1000*S2 if False else H+ 1e3*(S2-S*(S+1))**2*0
        # project to spin S: add penalty for S2 != S(S+1)
        P=S2-S*(S+1)*np.eye(len(D))
        w,v=np.linalg.eigh(H+1e4*(P@P))
        sel=w<1e3
        w=w[sel];v=v[:,sel]
        # cluster
        i=0
        while i<len(w):
            j=i+1
            while j<len(w) and w[j]-w[j-1]<1e-9:j+=1
            n=j-i
            ch=np.trace(v[:,i:j].conj().T@(C4[:,None]*v[:,i:j])).real
            lab={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}[(n,int(round(ch)))]
            res.append((w[i],f"{2*S+1}{lab}g",n))
            i=j
    res.sort()
    return res
if __name__=="__main__":
    pts=[]
    for x in np.arange(0,4.01,.5):
        r=levels(max(x,1e-7))
        g=r[0][0]
        lv=[{"term":t,"e_over_b":round(float(e-g),4)} for e,t,n in r[:6]]
        print(x,[(l['term'],l['e_over_b']) for l in lv])
        pts.append({"dq_over_b":float(x),"levels":lv})
    json.dump(pts,open('pts.json','w'))
E
python3 t.py 2>&1 | grep -v Matplotlib