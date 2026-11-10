python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
B,C=803.0,3078.0
F4=441*C/35.0; F2=(441*B+5*F4)/9.0
Fk={0:0.0,2:F2,4:F4}
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth); th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
ms=list(range(-2,3)); Yd={m:sph_harm_y(2,m,TH,PH) for m in ms}
Vsp={}
for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    tot=0
    for k in (0,2,4):
        s=0
        for q in range(-k,k+1):
            Yk=sph_harm_y(k,q,TH,PH)
            s+=np.sum(W*np.conj(Yd[m1])*np.conj(Yk)*Yd[m3])*np.sum(W*np.conj(Yd[m2])*Yk*Yd[m4])
        tot+=Fk[k]*4*np.pi/(2*k+1)*s
    Vsp[(m1,m2,m3,m4)]=tot.real
so=[(m,s) for m in ms for s in (0,1)]
N=10
Vt=np.zeros((N,)*4)
for a,b,c,d in itertools.product(range(N),repeat=4):
    if so[a][1]==so[c][1] and so[b][1]==so[d][1]: Vt[a,b,c,d]=Vsp[(so[a][0],so[b][0],so[c][0],so[d][0])]
print("sum all Vt", Vt.sum(), "sum direct", sum(Vt[a,b,a,b] for a in range(N) for b in range(N)), "sum exch", sum(Vt[a,b,b,a] for a in range(N) for b in range(N)))
print("Vsp sample", Vsp[(2,-2,-2,2)], Vsp[(2,2,2,2)], Vsp[(0,0,0,0)])
EOF