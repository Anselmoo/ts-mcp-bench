import numpy as np, itertools, math, json
from sympy.physics.wigner import gaunt as sg
B=806.0; C=3570.0
F4=441*C/35.0; F2=(441*B+5*F4)/9.0
Fk={2:F2,4:F4}
ms=[-2,-1,0,1,2]
gt={}
for K in (2,4):
    for a in ms:
        for b in ms:
            for c in range(-K,K+1):
                gt[(K,a,b,c)]=float(sg(2,2,K,a,b,c))
def Vorb(mi,mk,mj,ml):
    tot=0.0
    for K in (2,4):
        s=0.0
        for q in range(-K,K+1):
            I1=(-1)**(mi+q)*gt[(K,-mi,mk,-q)]
            I2=(-1)**mj*gt[(K,-mj,ml,q)]
            s+=I1*I2
        tot+=Fk[K]*4*math.pi/(2*K+1)*s
    return tot
mm=[ms[p//2] for p in range(10)]
ss=[p%2 for p in range(10)]
Vf=np.zeros((10,10,10,10))
for i,j,k,l in itertools.product(range(10),repeat=4):
    if ss[i]==ss[k] and ss[j]==ss[l]:
        Vf[i,j,k,l]=Vorb(mm[i],mm[k],mm[j],mm[l])
combos=list(itertools.combinations(range(10),5))
idx={c:n for n,c in enumerate(combos)}
N=len(combos)
def apply(occ,seq):
    occ=list(occ); sign=1
    for typ,p in seq:
        if typ=='a':
            if p not in occ: return None,0
            pos=occ.index(p); sign*=(-1)**pos; occ.pop(pos)
        else:
            if p in occ: return None,0
            pos=sum(1 for x in occ if x<p); sign*=(-1)**pos; occ.insert(pos,p)
    return tuple(occ),sign
u=[]
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
r2=math.sqrt(2)
u.append(vec({0:1}))
u.append(vec({2:1/r2,-2:1/r2}))
u.append(vec({-2:1/(1j*r2),2:-1/(1j*r2)}))
u.append(vec({-1:1/r2,1:-1/r2}))
u.append(vec({-1:1j/r2,1:1j/r2}))
eps=[6,6,-4,-4,-4]
def cubic(Dq):
    h=np.zeros((5,5),complex)
    for a in range(5):
        h+=eps[a]*Dq*np.outer(u[a],u[a].conj())
    return h
# Coulomb part (independent of Dq)
HEE=np.zeros((N,N))
for n,occ in enumerate(combos):
    for k in occ:
        for l in occ:
            if l==k: continue
            for i in range(10):
                for j in range(10):
                    if i==j: continue
                    v=Vf[i,j,k,l]
                    if v==0: continue
                    res,sg_=apply(occ,[('a',k),('a',l),('c',j),('c',i)])
                    if res is None: continue
                    HEE[idx[res],n]+=0.5*v*sg_
# one-body operator basis for cubic field: for each m-m' element
HONE={}
for a in range(5):
    for b in range(5):
        M=np.zeros((N,N),complex)
        for n,occ in enumerate(combos):
            for p in range(10):
                for q in range(10):
                    if ss[p]!=ss[q] or mm[p]+2!=a or mm[q]+2!=b: continue
                    res,sg_=apply(occ,[('a',q),('c',p)])
                    if res is None: continue
                    M[idx[res],n]+=sg_
        HONE[(a,b)]=M
def build_H(Dq):
    hm=cubic(Dq)
    H=HEE.astype(complex)
    for (a,b),M in HONE.items():
        H=H+hm[a,b]*M
    return H
Sz=np.zeros((N,N)); Sp=np.zeros((N,N))
for n,occ in enumerate(combos):
    Sz[n,n]=sum(0.5 if ss[p]==0 else -0.5 for p in occ)
    for m in ms:
        p_up=2*(m+2); p_dn=2*(m+2)+1
        res,sg_=apply(occ,[('a',p_dn),('c',p_up)])
        if res is not None: Sp[idx[res],n]+=sg_
Sm=Sp.T
S2=Sm@Sp+Sz@Sz+Sz
Lz=np.diag(np.array(ms,complex))
Lp=np.zeros((5,5),complex)
for m in ms[:-1]:
    Lp[m+1+2,m+2]=math.sqrt(6-m*(m+1))
Lm=Lp.conj().T
Lx=(Lp+Lm)/2; Ly=(Lp-Lm)/(2j)
from scipy.linalg import expm
def Rmat(axis,th):
    n=np.array(axis,float); n/=np.linalg.norm(n)
    G=n[0]*Lx+n[1]*Ly+n[2]*Lz
    return expm(-1j*th*G)
def Omega_from_R(R5):
    M=np.zeros((10,10),complex)
    for p in range(10):
        for q in range(10):
            if ss[p]==ss[q]: M[p,q]=R5[mm[p]+2,mm[q]+2]
    Om=np.zeros((N,N),complex)
    for n,S in enumerate(combos):
        for t,T in enumerate(combos):
            Om[t,n]=np.linalg.det(M[np.ix_(list(T),list(S))])
    return Om
reps=[Rmat([0,0,1],0),Rmat([1,1,1],2*math.pi/3),Rmat([0,0,1],math.pi),
      Rmat([0,0,1],math.pi/2),Rmat([1,1,0],math.pi)]
Oms=[Omega_from_R(R) for R in reps]
classes=[1,8,3,6,6]
chartab={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],
         'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
def decompose(chis):
    out={}
    for name,ct in chartab.items():
        n=sum(classes[c]*chis[c]*ct[c] for c in range(5))/24.0
        out[name]=int(round(n.real))
    return out
def levels(Dq):
    H=build_H(Dq)
    s2vals,s2vecs=np.linalg.eigh((S2+S2.T)/2)
    res=[]
    for S in (5/2,3/2,1/2):
        sel=np.abs(s2vals-S*(S+1))<1e-6
        W=s2vecs[:,sel]
        if W.shape[1]==0: continue
        Hs=W.conj().T@H@W
        Hs=(Hs+Hs.conj().T)/2
        ev,X=np.linalg.eigh(Hs)
        V=W@X
        i=0
        while i<len(ev):
            j=i
            while j+1<len(ev) and abs(ev[j+1]-ev[i])<1e-5: j+=1
            Vc=V[:,i:j+1]
            chis=[np.trace(Vc.conj().T@Om@Vc) for Om in Oms]
            dec=decompose(chis)
            for name,nm in dec.items():
                for _ in range(nm):
                    res.append((ev[i],int(round(2*S+1)),name))
            i=j+1
    res.sort(key=lambda x:x[0])
    return res
if __name__=="__main__":
    out=[]
    for x in [0.5*k for k in range(9)]:
        lv=levels(x*B)
        E0=lv[0][0]
        lst=[{'term':f"{m}{nm}",'E_over_B':round((E-E0)/B,4)} for E,m,nm in lv[:6]]
        out.append({'Dq_over_B':x,'levels':lst})
        print(x, [(l['term'],l['E_over_B']) for l in lst], flush=True)
    json.dump(out,open('result.json','w'),indent=1)
