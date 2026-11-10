import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import fsolve
# real d orbitals as functions of (theta, phi): build via complex Y_2m then combine
def Ylm(l,m,th,ph): return sph_harm(abs(m), l, ph, th) if m>=0 else None
def cY(m,th,ph):  # complex Y_2m
    return sph_harm(m, 2, ph, th)
def real_orb(th,ph):
    s2=1/np.sqrt(2)
    out=[]
    # xy, yz, xz, x2-y2, z2 (standard real combinations)
    Y={m:cY(m,th,ph) for m in range(-2,3)}
    out.append(1j*(Y[-2]-Y[2])*s2)     # ~ xy
    out.append(1j*(Y[-1]+Y[1])*s2)     # ~ yz
    out.append((Y[-1]-Y[1])*s2)        # ~ xz
    out.append((Y[-2]+Y[2])*s2)        # ~ x2-y2
    out.append(Y[0])                   # z2
    return out
# quadrature grid
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.linspace(0,2*np.pi,nph,endpoint=False)
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
orbs=[np.array(f) for f in real_orb(TH,PH)]
orbs=[np.conj(f)*0+f for f in orbs]
# normalise
for i in range(5):
    n=np.sum(W*np.abs(orbs[i])**2); orbs[i]=orbs[i]/np.sqrt(n)
# angular coefficient a^k(a,b,c,d) = 4pi/(2k+1) sum_q <a|Y_kq^*|c>... use <ab|1/r12|cd> = sum_k F^k a^k, 
# a^k = 4pi/(2k+1) sum_q  <a|Y_kq^*|c> <b|Y_kq|d>   (a,c on electron1; b,d on electron2)
def Ykq(k,q,th,ph): return sph_harm(q,k,ph,th)
def ak(k):
    A=np.zeros((5,5,5,5),complex)
    Ys={q:Ykq(k,q,TH,PH) for q in range(-k,k+1)}
    # matrix M_q[a,c]=<a|Y_kq^*|c>, N_q[b,d]=<b|Y_kq|d>
    for q in range(-k,k+1):
        M=np.array([[np.sum(W*np.conj(orbs[a])*np.conj(Ys[q])*orbs[c]) for c in range(5)] for a in range(5)])
        N=np.array([[np.sum(W*np.conj(orbs[b])*Ys[q]*orbs[d]) for d in range(5)] for b in range(5)])
        A+=np.einsum('ac,bd->abcd',M,N)
    return 4*np.pi/(2*k+1)*A
a0,a2,a4=ak(0),ak(2),ak(4)
# Fock space: spin-orbitals index p = 2*orb + s (s=0 up,1 down)
NS=10
states=[s for s in itertools.combinations(range(NS),3)]
idx={s:i for i,s in enumerate(states)}
D=len(states)
def apply_cdag_c(i,j,state_list):
    pass
def op_matrix_twobody(Vfun):
    # H2 = 1/2 sum <pq|V|rs> c+_p c+_q c_s c_r
    H=np.zeros((D,D))
    for si,s in enumerate(states):
        occ=list(s)
        for r in occ:
            for sidx in occ:
                pass
    return H
def apply_ops(p,q,r,s,st):
    # compute c+_p c+_q c_s c_r |st>, st tuple sorted; return (sign,newstate) or None
    occ=list(st); sign=1
    def annih(x,occ):
        if x not in occ: return None
        pos=occ.index(x); sg=(-1)**pos; occ=occ[:pos]+occ[pos+1:]; return sg,occ
    def create(x,occ):
        if x in occ: return None
        pos=sum(1 for y in occ if y<x); sg=(-1)**pos; occ=sorted(occ+[x]); return sg,occ
    res=annih(r,occ)
    if res is None: return None
    sg1,occ=res
    res=annih(s,occ)
    if res is None: return None
    sg2,occ=res
    res=create(q,occ)
    if res is None: return None
    sg3,occ=res
    res=create(p,occ)
    if res is None: return None
    sg4,occ=res
    return sg1*sg2*sg3*sg4, tuple(occ)
def build(F2,F4):
    H=np.zeros((D,D))
    # two-body: spin-orbital V_{pq,rs}= g(orb_p,orb_q,orb_r,orb_s)*delta(s_p,s_r)*delta(s_q,s_s)
    # g = F0 a0 + F2 a2 + F4 a4 (F0 contributes only constant? keep 0)
    G=F2*a2.real+F4*a4.real
    for p in range(NS):
      for q in range(NS):
        for r in range(NS):
          for s in range(NS):
            if (p%2)!=(r%2) or (q%2)!=(s%2): continue
            val=0.5*G[p//2,q//2,r//2,s//2]
            if abs(val)<1e-14: continue
            for j,st in enumerate(states):
                out=apply_ops(p,q,r,s,st)
                if out is None: continue
                sg,ns=out
                H[idx[ns],j]+=sg*val
    return H
def onebody_field(Dq):
    # eg (orbs 3,4) +6Dq, t2g (0,1,2) -4Dq ; spin independent
    eps=[-4*Dq]*3+[6*Dq]*2
    H=np.zeros((D,D))
    for j,st in enumerate(states):
        for p in st:
            H[j,j]+=eps[p//2]
    return H
# S^2 operator
def S2mat():
    Sz=np.zeros((D,D)); Sp=np.zeros((D,D))
    for j,st in enumerate(states):
        Sz[j,j]=sum(0.5 if p%2==0 else -0.5 for p in st)
    # S+ = sum_orb c+_{o,up} c_{o,down}
    for o in range(5):
        for j,st in enumerate(states):
            out=apply_ops(2*o,2*o,2*o+1,2*o+1,st) if False else None
    # simpler: build single-particle ops
    def cdag_c(p,q):
        M=np.zeros((D,D))
        for j,st in enumerate(states):
            out=apply_ops(p,p,q,q,st) if False else None
        return M
    return Sz
