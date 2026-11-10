from d3 import *
import collections
# real t2g orbitals as combos of complex m (dict m->coef), normalized
r2=np.sqrt(2)
t2g={'xy':{-2:1j/r2,2:-1j/r2},'xz':{-1:1/r2,1:-1/r2},'yz':{-1:1j/r2,1:1j/r2}}
def vec_from_ops(orb_list):
    # orb_list: list of (realname, spin) ; returns dict occ->coeff in complex Fock basis
    vecs={():1.0}
    for name,s in orb_list:
        new=collections.defaultdict(complex)
        for occ,c in vecs.items():
            for m,cm in t2g[name].items():
                idx_=so.index((m,s))
                r=apply_ops([('c',idx_)],occ)
                if r is None: continue
                sg,ns=r
                new[ns]+=c*cm*sg
        vecs=new
    return vecs
# build t2g^3 basis: choose 3 distinct spin-orbitals from 6 (3 orbitals x 2 spins)
spinorbs=[(n,s) for n in ['xy','xz','yz'] for s in (1,-1)]
basis=[]
for comb in itertools.combinations(spinorbs,3):
    v=vec_from_ops(list(comb))
    basis.append(v)
# gram / vectors in 120-dim
def tovec(v):
    x=np.zeros(120,dtype=complex)
    for occ,c in v.items(): x[sid[occ]]+=c
    return x
B=np.array([tovec(v) for v in basis]).T  # 120 x 20 (not orthonormal necessarily)
Q,R=np.linalg.qr(B)
# orthonormal basis for span
u,s,vh=np.linalg.svd(B,full_matrices=False)
Qb=u[:,s>1e-9]
print("dim t2g^3:",Qb.shape[1])
for F2,F4 in [(1.0,0.0),(0.0,1.0)]:
    H=build({0:0.0,2:F2,4:F4}).astype(complex)
    Ht=Qb.conj().T@H@Qb
    S2m=S2(); S2t=Qb.conj().T@S2m@Qb
    M=Ht+1e3*S2t
    w,v=np.linalg.eigh(M)
    res=[]
    for i in range(len(w)):
        x=v[:,i]
        res.append((round((x.conj()@S2t@x).real,3), round((x.conj()@Ht@x).real,5)))
    print(F2,F4, collections.Counter([a for a,b in res]))
    for S in sorted(set(a for a,b in res)):
        print(' S2=',S, sorted(set(b for a,b in res if a==S)))
