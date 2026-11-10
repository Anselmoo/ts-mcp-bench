
mkdir -p ~/w && cd ~/w && cat << 'EOF' > d7.py
import numpy as np, itertools, math
from sympy.physics.wigner import gaunt
from sympy import N as sN
B=1.0; F4=35*0+0
F4=441*0+0
C=3699/784; Bv=1.0
F4=441*C/35; F2=(441*Bv+5*F4)/9
Fk={0:0.0,2:F2,4:F4}
ms=list(range(-2,3))
def cLM(m,q,mp,k):
    # <l m|C^k_q|l mp>, l=2
    if m-mp!=q: return 0.0
    return float((-1)**m * gaunt(2,k,2,-m,q,mp))*math.sqrt(4*math.pi/(2*k+1))*0+ float((-1)**m*gaunt(2,k,2,-m,q,mp))*math.sqrt(4*math.pi/(2*k+1))
# Use Racah: <l m|C^k_q|l m'> ; the 1/r12 expansion: 1/r12 = sum_k (4pi/(2k+1)) sum_q Y*kq Y kq ... careful:
# 1/|r1-r2| = sum_k (r<^k/r>^{k+1}) sum_q (-1)^q C^k_q(1) C^k_{-q}(2), C^k_q=sqrt(4pi/(2k+1)) Y_kq
def cmat(m,q,mp,k):
    if m-mp!=q: return 0.0
    # Y_kq conj etc: <lm|C^k_q|lmp> = int Y_lm^* sqrt(4pi/(2k+1)) Y_kq Y_lmp
    return math.sqrt(4*math.pi/(2*k+1))*complex((-1)**m*float(gaunt(2,k,2,-m,q,mp)))
def g(m1,m2,m3,m4):
    # <m1 m2|1/r12|m3 m4> / radial-stripped: returns dict k->angular coefficient
    out={}
    for k in (0,2,4):
        s=0
        for q in range(-k,k+1):
            s+= (-1)**q * cmat(m1,q,m3,k)*cmat(m2,-q,m4,k)
        out[k]=s
    return out
# one-body CF in m-basis: orbitals real
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
r2=math.sqrt(2)
orbs={
 'dz2':(6,vec({0:1})),
 'dx2y2':(6,vec({2:1/r2,-2:1/r2})),
 'dxy':(-4,vec({2:1/(1j*r2),-2:-1/(1j*r2)})),
 'dxz':(-4,vec({1:-1/r2,-1:1/r2})),
 'dyz':(-4,vec({1:1j/r2,-1:1j/r2})),
}
h=np.zeros((5,5),complex)
for name,(e,v) in orbs.items():
    h+= e*np.outer(v,v.conj())
# 2e integrals in spin-orbital basis
spin=[(m,s) for m in ms for s in (1,-1)]
n=len(spin)
# build Hee matrix in determinant basis of 7 electrons
dets=list(itertools.combinations(range(n),7))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(det,ops):
    # ops list of (type,index) applied right to left: ops applied in order given (rightmost first)
    occ=list(det); sign=1
    for typ,i in ops:
        if typ=='a':   # annihilate
            if i not in occ: return None,0
            p=occ.index(i); sign*= (-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            # insert sorted
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
H=np.zeros((len(dets),len(dets)),complex)
# one-body
for a in range(n):
    for b in range(n):
        if spin[a][1]!=spin[b][1]: continue
        hv=h[spin[a][0]+2,spin[b][0]+2]
        if abs(hv)<1e-12: continue
        for j,d in enumerate(dets):
            new,s=apply_ops(d,[('c',a),('a',b)])  # c_a^+ c_b
            if new is None: continue
            H[idx[new],j]+=hv*s
# two-body: 1/2 sum <ab|g|cd> c+_a c+_b c_d c_c
for a,b,c,dd in itertools.product(range(n),repeat=4):
    if spin[a][1]!=spin[c][1] or spin[b][1]!=spin[dd][1]: continue
    m1,m2,m3,m4=spin[a][0],spin[b][0],spin[c][0],spin[dd][0]
    gg=g(m1,m2,m3,m4)
    val=sum(Fk[k]*gg[k] for k in (0,2,4)).real if True else 0
    if abs(val)<1e-12: continue
    for j,d in enumerate(dets):
        new,s=apply_ops(d,[('a',c),('a',dd),('c',b),('c',a)])
        if new is None: continue
        H[idx[new],j]+=0.5*val*s
# check hermitian
print("herm",np.abs(H-H.conj().T).max())
# S^2 via Sz sectors
Sz=np.array([sum(0.5*spin[i][1] for i in d) for d in dets])
def spec(mask):
    Hm=H[np.ix_(mask,mask)]
    return np.linalg.eigvalsh(Hm)
import sys
res={}
for Dq in [1.45,2.45,3.00]:
    pass
# full H with CF scaled by Dq: H = Hee + Dq*(CF with unit Dq)
Hcf=np.zeros_like(H)
# build CF one-body with Dq=1 units: h above is in units of Dq (6, -4)
for a in range(n):
    for b in range(n):
        if spin[a][1]!=spin[b][1]: continue
        hv=h[spin[a][0]+2,spin[b][0]+2]
        if abs(hv)<1e-12: continue
        for j,d in enumerate(dets):
            new,s=apply_ops(d,[('c',a),('a',b)])
            if new is None: continue
            Hcf[idx[new],j]+=hv*s
Hee=H-Hcf
quart=np.where(np.isclose(Sz,1.5))[0]
doub=np.where(np.isclose(Sz,0.5))[0]
Hq=Hee[np.ix_(quart,quart)]
Hq_full=Hee[np.ix_(quart,quart)]
for Dq in [1.45,2.45,3.00]:
    Hfull=Hee+Dq*Hcf/1.0
    # quartet sector
    eq=np.linalg.eigvalsh(Hfull[np.ix_(quart,quart)])
    ed=np.linalg.eigvalsh(Hfull[np.ix_(doub,doub)])
    # remove quartet eigenvalues from M=1/2 set
    ed=list(ed)
    for x in eq:
        j=min(range(len(ed)),key=lambda k:abs(ed[k]-x)); ed.pop(j)
    def levels(vals):
        vals=sorted(vals); out=[]
        for v in vals:
            if out and abs(out[-1][0]-v)<1e-6: out[-1][1]+=1
            else: out.append([v,1])
        return out
    Lq=levels(eq); Ld=levels(ed)
    g0=min(eq[0],ed[0])
    print("Dq",Dq,"ground",eq[0]-eq[0])
    print(" quartets", [(round(v-eq[0],4),m) for v,m in Lq])
    print(" doublets", [(round(v-eq[0],4),m) for v,m in Ld])
EOF
timeout 500 python3 d7.py