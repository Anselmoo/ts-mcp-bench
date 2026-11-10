import itertools, numpy as np
from sympy.physics.wigner import gaunt
from scipy.special import sph_harm
from math import pi
from functools import lru_cache
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]   # index=2*i+s
NS=10
@lru_cache(None)
def gnt(l1,l2,l3,m1,m2,m3):
    return float(gaunt(l1,l2,l3,m1,m2,m3))
def conjY_int(m1,k,q,m3):
    # ∫ Y_2^{m1*} Y_k^{q} Y_2^{m3}
    return (-1)**m1 * gnt(2,k,2,-m1,q,m3)
def Vrad(m1,m2,m3,m4,F):
    # <m1 m2|1/r12|m3 m4> with electron1: Y^{m1*}(1) Y^{m3}(1), electron2: Y^{m2*}(2) Y^{m4}(2)
    tot=0.0
    for k in (0,2,4):
        s=0.0
        for q in range(-k,k+1):
            # expansion: 1/r12 = Σ 4π/(2k+1) Σ_q Y_k^{q*}(1) Y_k^{q}(2)
            a=(-1)**q*conjY_int(m1,k,-q,m3)  # ∫Y^{m1*} Y_k^{q*} Y^{m3}; Y_k^{q*}=(-1)^q Y_k^{-q}
            b=conjY_int(m2,k,q,m4)            # ∫Y^{m2*} Y_k^{q} Y^{m4}
            s+=a*b
        tot+=4*pi/(2*k+1)*s*F[k]
    return tot
def twobody():
    V=np.zeros((NS,NS,NS,NS))
    for a,b,c,d in itertools.product(range(NS),repeat=4):
        ma,sa=orbs[a]; mb,sb=orbs[b]; mc,sc=orbs[c]; md,sd=orbs[d]
        if sa!=sc or sb!=sd: continue
        V[a,b,c,d]=(ma,mb,mc,md)  # placeholder
    return V
def build_V(F):
    V=np.zeros((NS,NS,NS,NS))
    for a,b,c,d in itertools.product(range(NS),repeat=4):
        ma,sa=orbs[a]; mb,sb=orbs[b]; mc,sc=orbs[c]; md,sd=orbs[d]
        if sa!=sc or sb!=sd: continue
        V[a,b,c,d]=Vrad(ma,mb,mc,md,F)   # <ab|cd>
    return V
def build_h(Dq):
    # octahedral point charges at ±x,±y,±z; angular part of r^4 term
    # Use numeric projection: h_{mm'} = ∫ Y_m^* V(Ω) Y_m', V(Ω)= Σ_i 1/|r-R_i| 4-th order term ∝ Σ_i P4(cos γ_i)
    # P4(cos γ) = 4π/9 Σ_q Y4^q*(n) Y4^q(r)
    dirs=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
    def angles(v):
        x,y,z=v; th=np.arccos(z); ph=np.arctan2(y,x); return th,ph
    # use quadrature on sphere
    nth,nph=40,80
    xs,ws=np.polynomial.legendre.leggauss(nth)
    th=np.arccos(xs); ph=np.linspace(0,2*pi,nph,endpoint=False); wph=2*pi/nph
    TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(ws,np.ones(nph))*wph
    # potential (angular): sum over ligands P4(cos gamma) ; eg/t2g splitting from it
    Vang=np.zeros_like(TH)
    for d in dirs:
        ct=np.cos(TH)*d[2]+np.sin(TH)*np.cos(PH)*d[0]+np.sin(TH)*np.sin(PH)*d[1]
        Vang+= (35*ct**4-30*ct**2+3)/8
    h=np.zeros((5,5),complex)
    for i,m in enumerate(ms):
        for j,mp in enumerate(ms):
            Yi=sph_harm(m,2,PH,TH); Yj=sph_harm(mp,2,PH,TH)
            h[i,j]=np.sum(np.conj(Yi)*Vang*Yj*W)
    ev=np.linalg.eigvalsh(h)
    return h, ev
if __name__=="__main__":
    h,ev=build_h(1)
    print(np.round(ev,4))
