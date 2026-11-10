import numpy as np, itertools
from scipy.special import sph_harm_y
B,C=803.0,3078.0
F4=441*C/35.0; F2=(441*B+5*F4)/9.0
# Check Racah/Slater relations numerically: d^2 3F vs 3P splitting should be -15B
def run(n):
    nth,nph=40,80
    x,w=np.polynomial.legendre.leggauss(nth); th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
    TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
    ms=range(-2,3); Yd={m:sph_harm_y(2,m,TH,PH) for m in ms}
    Fk={0:0.0,2:F2,4:F4}
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
    so=[(m,s) for m in ms for s in (0,1)]; N=10
    Vt=np.zeros((N,)*4)
    for a,b,c,d in itertools.product(range(N),repeat=4):
        if so[a][1]==so[c][1] and so[b][1]==so[d][1]: Vt[a,b,c,d]=Vsp[(so[a][0],so[b][0],so[c][0],so[d][0])]
    dets=[sum(1<<i for i in c) for c in itertools.combinations(range(N),n)]
    idx={d:i for i,d in enumerate(dets)}; D=len(dets)
    par=lambda x: -1 if bin(x).count('1')%2 else 1
    Hee=np.zeros((D,D))
    nz=[(a,b,c,d,Vt[a,b,c,d]) for a,b,c,d in itertools.product(range(N),repeat=4) if abs(Vt[a,b,c,d])>1e-12 and a!=b and c!=d]
    for col,st in enumerate(dets):
        for a,b,c,d,v in nz:
            if not (st>>c)&1: continue
            s1=par(st&((1<<c)-1)); t=st^(1<<c)
            if not (t>>d)&1: continue
            s2=par(t&((1<<d)-1)); t^=(1<<d)
            if (t>>b)&1: continue
            s3=par(t&((1<<b)-1)); t|=(1<<b)
            if (t>>a)&1: continue
            s4=par(t&((1<<a)-1)); t|=(1<<a)
            Hee[idx[t],col]+=0.5*v*s1*s2*s3*s4
    return Hee, np.linalg.eigvalsh(Hee)
H,ev=run(2)
u=np.unique(np.round(ev,3)); print("d2 levels:",u)
print("d2 trace/avg", np.trace(H)/len(ev))
