
cat << 'EOF' > /dev/shm/d6b.py
import numpy as np, itertools
exec(open('/dev/shm/d6.py').read().split('# spin-orbitals')[0])
def apply_ann(l,p):
    if p not in l: return None
    pos=l.index(p); return (-1)**pos, [q for q in l if q!=p]
def apply_cre(l,p):
    if p in l: return None
    s=(-1)**sum(1 for q in l if q<p); return s, sorted(l+[p])
def build_H(Dq,F2,F4):
    h1=np.array([6*Dq,-4*Dq,-4*Dq,-4*Dq,6*Dq])
    Vo=F2*G2+F4*G4
    states=list(itertools.combinations(range(10),6)); idx={s:i for i,s in enumerate(states)}
    n=len(states); H=np.zeros((n,n))
    for j,s in enumerate(states):
        l=list(s)
        for p in l: H[j,j]+=h1[p//2]
        for a,cc,b,dd in itertools.product(range(10),repeat=4):
            if a%2!=cc%2 or b%2!=dd%2: continue
            v=Vo[a//2,cc//2,b//2,dd//2]
            if abs(v)<1e-12: continue
            r=apply_ann(l,cc)
            if r is None: continue
            s1,l1=r
            r=apply_ann(l1,dd)
            if r is None: continue
            s2,l2=r
            r=apply_cre(l2,b)
            if r is None: continue
            s3,l3=r
            r=apply_cre(l3,a)
            if r is None: continue
            s4,l4=r
            H[idx[tuple(l4)],j]+=0.5*s1*s2*s3*s4*v
    return H,states
if __name__=='__main__':
    # check d2 free ion: F2,F4 -> B,C ; test 3P-3F = 15B using Ms=1 sector of d2 (M_L...) simple check: eigenvalues with 2 electrons
    pass
EOF
cd /dev/shm && python3 -c "
import numpy as np, itertools
exec(open('d6b.py').read().split(\"if __name__\")[0])
" && echo ok