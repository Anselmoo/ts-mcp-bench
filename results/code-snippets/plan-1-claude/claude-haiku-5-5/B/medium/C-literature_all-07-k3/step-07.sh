
cd /tmp/tsbench-run-uqj8uf3b && cat << 'EOF' > many.py
import numpy as np, itertools
D=np.load('data.npz'); H1=D['H1']; V0,V2,V4=D['V0'],D['V2'],D['V4']
# spin orbitals p = 2*orb + s, s=0 up, 1 down
states=[]
for occ in itertools.combinations(range(10),5): states.append(occ)
idx={s:i for i,s in enumerate(states)}
def apply_cdag_c(occ, p, q):
    # c^dag_p c_q on determinant occ (sorted tuple of occupied); return (sign,newocc) or None
    occl=list(occ)
    if q not in occl: return None
    sgn=(-1)**sum(1 for x in occl if x<q); occl.remove(q)
    if p in occl: return None
    sgn*= (-1)**sum(1 for x in occl if x<p); occl.append(p); occl.sort()
    return sgn, tuple(occl)
def apply_2(occ,p,r,s,q):
    # c^dag_p c^dag_r c_s c_q  (apply c_q, then c_s, then c^dag_r, then c^dag_p)
    res=apply_cdag_c(occ,s,q) if False else None
    occl=list(occ); sgn=1
    # c_q
    if q not in occl: return None
    sgn*=(-1)**sum(1 for x in occl if x<q); occl.remove(q)
    if s not in occl: return None
    sgn*=(-1)**sum(1 for x in occl if x<s); occl.remove(s)
    if r in occl: return None
    sgn*=(-1)**sum(1 for x in occl if x<r); occl.append(r); occl.sort()
    if p in occl: return None
    sgn*=(-1)**sum(1 for x in occl if x<p); occl.append(p); occl.sort()
    return sgn, tuple(occl)
N=len(states)
def build(hfun_1, Vfull):
    # hfun_1: 10x10 one-body matrix; Vfull: 10x10x10x10 two-body <pq|V|rs> (spin-orbital)
    Hm=np.zeros((N,N),complex)
    for j,occ in enumerate(states):
        for p in range(10):
            for q in range(10):
                if abs(hfun_1[p,q])<1e-14: continue
                r=apply_cdag_c(occ,p,q)
                if r: Hm[idx[r[1]],j]+=hfun_1[p,q]*r[0]
        for p in range(10):
          for q in range(10):
            for r_ in range(10):
              for s in range(10):
                v=Vfull[p,q,r_,s]
                if abs(v)<1e-14: continue
                res=apply_2(occ,p,q,s,r_)  # c^dag_p c^dag_q c_s c_r ; <pq|V|rs> -> 1/2 sum
                if res: Hm[idx[res[1]],j]+=0.5*v*res[0]
    return Hm
def spin_orb(one_orb, two_orb):
    h=np.zeros((10,10),complex); h[:, :]=0
    for a in range(5):
        for b in range(5):
            for s in range(2):
                h[2*a+s,2*b+s]=one_orb[a,b]
    V=np.zeros((10,)*4,complex)
    for a in range(5):
        for b in range(5):
            for c in range(5):
                for e in range(5):
                    for s in range(2):
                        for t in range(2):
                            V[2*a+s,2*b+t,2*c+s,2*e+t]=two_orb[a,b,c,e]
    return h,V
# sector selection
def nup(occ): return sum(1 for p in occ if p%2==0)
def ndn(occ): return sum(1 for p in occ if p%2==1)
sec=[i for i,o in enumerate(states) if nup(o)-ndn(o)==3]
sec5=[i for i,o in enumerate(states) if nup(o)-ndn(o)==5]
# Angular-Slater tensor: V = F0*V0 + F2*V2 + F4*V4
def spectrum(Dq,B,C):
    F0=0.0; F2=49*B+7*C; F4=12.6*C
    h1=Dq*H1.real
    two=F0*V0+F2*V2+F4*V4
    h,V=spin_orb(h1,two)
    Hm=build(h,V)
    return Hm
if __name__=="__main__":
    Hm=spectrum(1.0,0.0,0.0)
    print(np.allclose(Hm,Hm.conj().T))
EOF
python3 many.py