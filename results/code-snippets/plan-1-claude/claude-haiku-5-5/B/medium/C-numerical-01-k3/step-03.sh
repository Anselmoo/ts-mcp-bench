mkdir -p /w && cat > /w/d2.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2; ms=list(range(-2,3))
def w3(a,b,c,d,e,f): return float(wigner_3j(a,b,c,d,e,f))
def V_ee(F):  # F dict k->value ; returns 5^4 array <ma mb|1/r|mc md>
    M=np.zeros((5,5,5,5))
    for i,ma in enumerate(ms):
     for j,mb in enumerate(ms):
      for k_,mc in enumerate(ms):
       for n,md in enumerate(ms):
        s=0
        for k in (0,2,4):
          g=(2*l+1)**2*w3(l,k,l,0,0,0)**2
          t=0
          for q in range(-k,k+1):
            t+=(-1)**q*w3(l,k,l,-ma,q,mc)*w3(l,k,l,-mb,-q,md)
          s+=F[k]*g*t*(-1)**(ma+mb) if False else F[k]*g*t
        M[i,j,k_,n]=s
    return M
# Build Ms=1 determinants: two spin-up electrons in orbitals m (5 orbitals)
dets=list(itertools.combinations(range(5),2))
def H(F,Dq):
    M=V_ee(F)
    n=len(dets); H=np.zeros((n,n))
    # one-body: h = -4Dq + 10Dq*Peg, Peg = |0><0| + 1/2 (|2>+|-2>)(<2|+<-2|)
    Peg=np.zeros((5,5)); Peg[2,2]=1
    v=np.zeros(5); v[0]=1; v[4]=1
    Peg[np.ix_([0,4],[0,4])]+=0.5*np.ones((2,2))
    Peg[2,2]=1
    h=-4*Dq*np.eye(5)+10*Dq*Peg
    for I,(a,b) in enumerate(dets):
      for J,(c,d) in enumerate(dets):
        val=0
        # one-body
        if b==d: val+=h[a,c]
        if a==d: val-=h[b,c]*0  # placeholder
        # build via explicit determinant (simple, both spin up): use Slater rules
        occI=[a,b]; occJ=[c,d]
        H[I,J]=0
    return None
EOF
echo