import numpy as np, itertools
from scipy.optimize import fsolve
from scipy.special import eval_legendre
# quadrature on sphere
nt, nphi = 40, 80
xg, wg = np.polynomial.legendre.leggauss(nt)
pts=[];w=[]
for ct,wt in zip(xg,wg):
    st=np.sqrt(1-ct*ct)
    for j in range(nphi):
        ph=2*np.pi*j/nphi
        pts.append([st*np.cos(ph),st*np.sin(ph),ct]); w.append(wt*2*np.pi/nphi)
P=np.array(pts); W=np.array(w)
x,y,z=P.T
# real d orbitals (unit-sphere angular parts), order: xy,yz,zx,z2,x2y2
orbs=[np.sqrt(15/(4*np.pi))*x*y, np.sqrt(15/(4*np.pi))*y*z, np.sqrt(15/(4*np.pi))*z*x,
      np.sqrt(5/(16*np.pi))*(3*z*z-1), np.sqrt(15/(16*np.pi))*(x*x-y*y)]
O=np.array(orbs)  # 5 x N
G=P@P.T; G=np.clip(G,-1,1)
Pk={k:eval_legendre(k,G) for k in (0,2,4)}
def Ang(k):
    # A[a,c,b,d] = int psi_a psi_c(1) P_k psi_b psi_d(2)
    rho=np.einsum('an,cn,n->acn',O,O,W)  # 5x5xN
    M=np.einsum('acn,nm,bdm->acbd', rho, Pk[k]*1.0, rho, optimize=True)
    return M
A={k:Ang(k) for k in (0,2,4)}
def Vtensor(B,C):
    F4=441*C/35.0
    F2=(441*B+5*F4)/9.0
    F0=0.0
    return F0*A[0]+F2*A[2]+F4*A[4]
# Fock space: 10 spin orbitals: index = 2*orb + spin (0 up,1 down)
ndet=None
def states(ne):
    out=[]
    for c in itertools.combinations(range(10),ne):
        out.append(sum(1<<i for i in c))
    return out
def build(Dq,B,C):
    eps=np.zeros(10)
    for o in range(5):
        e = -6*Dq if o>=3 else 4*Dq   # Td: e (z2,x2y2) low, t2 high
        eps[2*o]=eps[2*o+1]=e
    Vt=Vtensor(B,C)
    basis=[s for s in states(8) if (bin(s & sum(1<<(2*o) for o in range(5))).count('1')==5)]
    # Ms=1: n_up=5, n_down=3
    basis=[s for s in states(8) if bin(s & 0b0101010101).count('1')==5]
    idx={s:i for i,s in enumerate(basis)}
    H=np.zeros((len(basis),)*2)
    def occ(s): return [i for i in range(10) if s>>i &1]
    for i,s in enumerate(basis):
        for p in occ(s): H[i,i]+=eps[p]
    # two-body: 1/2 sum V_{ijkl} a_i^+ a_j^+ a_l a_k with V_ijkl=<ij|V|kl>
    spin=lambda p: p%2
    orb=lambda p: p//2
    for i,s in enumerate(basis):
        o_list=occ(s)
        for k in o_list:
            for l in o_list:
                if l==k: continue
                # a_l a_k acting: annihilate k then l
                # use general: for j, i' creation
                pass
    # simpler: loop over pairs of occupied (k<l) and all pairs (p<q) of final
    for i,s in enumerate(basis):
        ol=occ(s)
        for a_ in range(len(ol)):
            for b_ in range(a_+1,len(ol)):
                k,l=ol[a_],ol[b_]
                # annihilate k,l -> state t, then create p,q
                t=s & ~(1<<k) & ~(1<<l)
                for p in range(10):
                    for q in range(p+1,10):
                        if t>>p &1 or t>>q &1: continue
                        # operator sum over ordered: 1/2 sum_{ijkl} V_{ij,kl} a+_i a+_j a_l a_k
                        # for pair set {k,l}->{p,q}: contributions amplitude
                        # matrix element <p q|V|k l> direct minus exchange
                        def amp(pp,qq,kk,ll):
                            if spin(pp)!=spin(kk) or spin(qq)!=spin(ll):
                                return 0.0
                            return Vt[orb(pp),orb(kk),orb(qq),orb(ll)]
                        # direct: <pq|V|kl> with spins; exchange: <pq|V|lk>
                        val=0.0
                        for (pp,qq) in [(p,q),(q,p)]:
                            for (kk,ll) in [(k,l),(l,k)]:
                                pass
                        # build full sign-correct element via determinant sign
                        sgn_val = 0.0
                        # matrix element of (1/2) sum V a+p a+q a_l a_k : use standard
                        # <pq|V|kl> = V(p,k,q,l) with 1/2 factor summing both orderings -> just direct+exchange
                        d = amp(p,q,k,l) - amp(p,q,l,k)
                        if d==0: continue
                        # sign from ordering: final state ordering (p<q) and initial (k<l)
                        # compute fermionic sign: create/annihilate sequence
                        def sign_apply(state, ops):
                            sg=1
                            st=state
                            for typ,ix in ops:
                                if typ=='a':
                                    n=bin(st & ((1<<ix)-1)).count('1')
                                    sg*= (-1)**n; st&=~(1<<ix)
                                else:
                                    n=bin(st & ((1<<ix)-1)).count('1')
                                    sg*= (-1)**n; st|=(1<<ix)
                            return sg,st
                        sg,res=sign_apply(s,[('a',l),('a',k),('c',q),('c',p)])
                        # careful: we need a_q+ a_p+ a_l a_k ordering; do explicit
                        if res!=t|(1<<p)|(1<<q): continue
                        H[idx[t|(1<<p)|(1<<q)], i] += 0  # placeholder
                        # fill via direct computation below
        # no-op
    return basis,idx,H,eps,Vt
