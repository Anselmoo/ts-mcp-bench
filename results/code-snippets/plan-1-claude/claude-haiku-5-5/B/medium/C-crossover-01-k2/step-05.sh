cat << 'EOF' > d4.py
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2; ms=list(range(-2,3))
so=[(m,s) for m in ms for s in (1,-1)]
def C_me(m,k,q,mp):
    if m!=mp+q: return 0.0
    return float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp)*(-1)**l*(2*l+1)*wigner_3j(l,k,l,0,0,0))
def ang(k,a,c,b,d):
    return sum((-1)**q*C_me(a,k,q,c)*C_me(b,k,-q,d) for q in range(-k,k+1))
def Vel(i,j,k_,l_,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[i],so[j],so[k_],so[l_]
    if sa!=sc or sb!=sd: return 0.0
    return sum(F[k]*ang(k,ma,mc,mb,md) for k in (2,4))
r2=np.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
orb={'z2':vec({0:1}),'x2y2':vec({2:1/r2,-2:1/r2}),'xy':vec({2:-1j/r2,-2:1j/r2}),
     'xz':vec({1:-1/r2,-1:1/r2}),'yz':vec({1:-1j/r2,-1:-1j/r2})}
P=np.zeros((5,5),complex)
for name,w in [('xy',-4),('xz',-4),('yz',-4),('z2',6),('x2y2',6)]:
    v=orb[name]; P+=w*np.outer(v,v.conj())
dets=list(itertools.combinations(range(10),4)); idx={d:n for n,d in enumerate(dets)}; N=len(dets)
def apply_ann(st,p):
    if p not in st: return None
    pos=st.index(p); return ((-1)**pos, tuple(x for x in st if x!=p))
def apply_cre(st,p):
    if p in st: return None
    pos=sum(1 for x in st if x<p); return ((-1)**pos, tuple(sorted(st+(p,))))
def op_matrix(terms):
    M=np.zeros((N,N))
    for n,d in enumerate(dets):
        for coef,ops in terms:
            st=d; sign=1; ok=True
            for typ,p in reversed(ops):
                r=apply_ann(st,p) if typ=='a' else apply_cre(st,p)
                if r is None: ok=False;break
                s,st=r; sign*=s
            if ok: M[idx[st],n]+=coef*sign
    return M
def build_parts(B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0; F={2:F2,4:F4}
    terms=[]
    for i,j,k_,l_ in itertools.product(range(10),repeat=4):
        v=Vel(i,j,k_,l_,F)
        if abs(v)<1e-12: continue
        terms.append((0.5*v,[('c',i),('c',j),('a',l_),('a',k_)]))
    Hee=op_matrix(terms)
    t1=[]
    for i,(m1,s1) in enumerate(so):
        for j,(m2,s2) in enumerate(so):
            if s1==s2 and abs(P[m1+2,m2+2])>1e-12:
                t1.append((P[m1+2,m2+2].real,[('c',i),('a',j)]))
    Hf=op_matrix(t1)
    Sp=op_matrix([(1.0,[('c',so.index((m,1))),('a',so.index((m,-1)))]) for m in ms])
    Sz=np.diag([sum(0.5*so[p][1] for p in d) for d in dets])
    S2=Sp.T@Sp+Sz@Sz+Sz
    return Hee,Hf,S2
EOF
python3 -c "
import d4,numpy as np
Hee,Hf,S2=d4.build_parts(706,2734)
print(np.allclose(Hee,Hee.T), np.allclose(Hf,Hf.T))
print(np.unique(np.round(np.linalg.eigvalsh(S2),3)))
print(np.unique(np.round(np.linalg.eigvalsh(Hf),3)))
"