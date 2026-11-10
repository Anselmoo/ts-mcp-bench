pip list 2>/dev/null | grep -i -E "sympy|numpy"; cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=821.;C=3657.
def run(N,Dq,B=821.,C=3657.):
    F4=C/35;F2=B+5*F4;Fs={0:0,2:49*F2,4:441*F4}
    # c^k(l m, l m') = sqrt(4pi/(2k+1)) * ... use <Y_lm|Y_kq|Y_lm'> gaunt
    ms=[-2,-1,0,1,2]
    def ck(m1,m2,k):  # <2 m1|C^k_{m1-m2}|2 m2>
        q=m1-m2
        if abs(q)>k: return 0.
        return float((-1)**m1*np.sqrt((2*k+1)/(4*np.pi))*0+0) if False else float(gaunt(2,k,2,-m1,q,m2)*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))*(1))
    # <ab|g|cd> spatial = sum_k c^k(a,c)c^k(d,b)F^k, q = ma-mc
    def g(a,b,c,d):
        if a+b!=c+d: return 0.
        s=0
        for k in (0,2,4):
            s+=ck(a,c,k)*ck(d,b,k)*Fs[k]/(1 if k==0 else (49 if k==2 else 441))*(1 if k==0 else 1)
        return s
    # use Slater F^k directly: Fs already F^k? we defined Fs=D*F_k = Slater; divide above wrongly. fix:
    def g(a,b,c,d):
        if a+b!=c+d: return 0.
        return sum(ck(a,c,k)*ck(d,b,k)*Fs[k] for k in (2,4))
    # one-body
    idx={m:i for i,m in enumerate(ms)}
    def vec(d):
        v=np.zeros(5,complex)
        for m,c in d.items(): v[idx[m]]=c
        return v
    s=2**-.5
    eg=[vec({0:1}),vec({2:s,-2:s})]
    t2=[vec({2:s,-2:-s}),vec({1:1}),vec({-1:1})]
    h=sum(-6*Dq*np.outer(v,v.conj()) for v in eg)+sum(4*Dq*np.outer(v,v.conj()) for v in t2)
    so=[(m,s_) for s_ in (0,1) for m in ms]
    n=10
    H1=np.zeros((n,n),complex);
    for i,(m,s_) in enumerate(so):
        for j,(m2,s2) in enumerate(so):
            if s_==s2:H1[i,j]=h[idx[m],idx[m2]]
    G=np.zeros((n,n,n,n))
    for a,(ma,sa) in enumerate(so):
     for b,(mb,sb) in enumerate(so):
      for c,(mc,sc) in enumerate(so):
       for d,(md,sd) in enumerate(so):
        if sa==sc and sb==sd: G[a,b,c,d]=g(ma,mb,mc,md)
    # H = sum h_ij a†i aj + 1/2 sum G_abcd a†a a†b b_d a_c ... <ab|g|cd>: a†a a†b a_d a_c
    dets=list(itertools.combinations(range(n),N));di={d:i for i,d in enumerate(dets)}
    def ap(op,det,create):
        l=list(det)
        if create:
            if op in l:return None
            pos=sum(1 for x in l if x<op);l.insert(pos,op);return tuple(l),(-1)**pos
        if op not in l:return None
        pos=l.index(op);l.pop(pos);return tuple(l),(-1)**pos
    H=np.zeros((len(dets),len(dets)),complex)
    for j,dt in enumerate(dets):
        for p in range(n):
         for q in range(n):
            if abs(H1[p,q])<1e-12:continue
            r=ap(q,dt,False)
            if r is None:continue
            r2=ap(p,r[0],True)
            if r2 is None:continue
            H[di[r2[0]],j]+=H1[p,q]*r[1]*r2[1]
        for c in range(n):
         for d in range(n):
          r=ap(c,dt,False)
          if r is None:continue
          r1=ap(d,r[0],False)
          if r1 is None:continue
          sg=r[1]*r1[1]
          # order: a†a a†b a_d a_c -> apply a_c first then a_d
          for a in range(n):
           for b in range(n):
            gv=G[a,b,c,d]
            if abs(gv)<1e-12:continue
            r2=ap(b,r1[0],True)
            if r2 is None:continue
            r3=ap(a,r2[0],True)
            if r3 is None:continue
            H[di[r3[0]],j]+=0.5*gv*sg*r2[1]*r3[1]
    return H,dets
import sys
H,d=run(2,0.0);e=np.linalg.eigvalsh(H);e=np.round(e-e[0],1);print(sorted(set(e))[:4],B)
for x in (0.90,2.15,3.35):
    H,d=run(4,x*B);
    # spin: compute Sz and S2? use degeneracies instead
    w=np.linalg.eigvalsh(H);w=w-w[0]
    # group levels
    lv=[];
    for v in w:
        if not lv or abs(v-lv[-1][0])>1e-3: lv.append([v,1])
        else: lv[-1][1]+=1
    print(x,[(round(v/B,3),k) for v,k in lv[:8]])
E
python3 /tmp/a.py