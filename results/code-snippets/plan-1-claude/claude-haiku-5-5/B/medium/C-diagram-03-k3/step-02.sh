mkdir -p /tmp/ts && cat > /tmp/ts/ts.py << 'EOF'
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
# spin-orbital p=2*(m+2)+s, s=0 up, 1 down
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
# cubic field in m basis
eg_ = {}
u=[]
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
r2=math.sqrt(2)
u.append(vec({0:1}))                      # dz2 (eg)
u.append(vec({2:1/r2,-2:1/r2}))           # dx2-y2 (eg)
u.append(vec({-2:1/(1j*r2),2:-1/(1j*r2)}))# dxy (t2g)
u.append(vec({-1:1/r2,1:-1/r2}))          # dxz (t2g)
u.append(vec({-1:1j/r2,1:1j/r2}))         # dyz (t2g)
eps=[6,6,-4,-4,-4]
def cubic(Dq):
    h=np.zeros((5,5),complex)
    for a in range(5):
        h+=eps[a]*Dq*np.outer(u[a],u[a].conj())
    return h
def build_H(Dq):
    H=np.zeros((N,N),complex)
    # two-electron
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
                        H[idx[res],n]+=0.5*v*sg_
    # cubic one-body
    hm=cubic(Dq)
    for n,occ in enumerate(combos):
        for p in range(10):
            for q in range(10):
                if ss[p]!=ss[q]: continue
                h=hm[mm[p]+2,mm[q]+2]
                if abs(h)<1e-14: continue
                res,sg_=apply(occ,[('a',q),('c',p)])
                if res is None: continue
                H[idx[res],n]+=h*sg_
    return H
# spin operators
Sz=np.zeros((N,N)); Sp=np.zeros((N,N))
for n,occ in enumerate(combos):
    Sz[n,n]=sum(0.5 if ss[p]==0 else -0.5 for p in occ)
    for m in ms:
        p_up=2*(m+2); p_dn=2*(m+2)+1
        res,sg_=apply(occ,[('a',p_dn),('c',p_up)])
        if res is not None: Sp[idx[res],n]+=sg_
Sm=Sp.T
S2=Sm@Sp+Sz@Sz+Sz
# rotation operators
def Lops():
    Lz=np.diag(np.array(ms,complex))
    Lp=np.zeros((5,5),complex)
    for m in ms[:-1]:
        Lp[m+1+2,m+2]=math.sqrt(2*3-m*(m+1))  # l=2
    Lm=Lp.conj().T
    Lx=(Lp+Lm)/2; Ly=(Lp-Lm)/(2j)
    return Lx,Ly,Lz
Lx,Ly,Lz=Lops()
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
        sub_cols=list(S)
        for t,T in enumerate(combos):
            Om[t,n]=np.linalg.det(M[np.ix_(list(T),sub_cols)])
    return Om
reps=[('E',1,Rmat([0,0,1],0)),
      ('C3',8,Rmat([1,1,1],2*math.pi/3)),
      ('C2',3,Rmat([0,0,1],math.pi)),
      ('C4',6,Rmat([0,0,1],math.pi/2)),
      ('C2p',6,Rmat([1,1,0],math.pi))]
Oms=[Omega_from_R(R) for _,_,R in reps]
classes=[1,8,3,6,6]
chartab={'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],
         'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
def decompose(chis):
    out={}
    for name,ct in chartab.items():
        n=sum(classes[c]*chis[c]*ct[c] for c in range(5))/24.0
        out[name]=int(round(n.real))
    return out
spinname={}
def levels(Dq):
    H=build_H(Dq)
    # spin sectors
    s2vals,s2vecs=np.linalg.eigh((S2+S2.conj().T)/2)
    res=[]
    for S in (5/2,3/2,1/2):
        sel=np.abs(s2vals-S*(S+1))<1e-6
        W=s2vecs[:,sel]
        if W.shape[1]==0: continue
        Hs=W.conj().T@H@W
        Hs=(Hs+Hs.conj().T)/2
        ev,X=np.linalg.eigh(Hs)
        V=W@X
        # group clusters
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
    import sys
    gridpts=[x*0.5 for x in range(9)]
    out=[]
    for x in gridpts:
        lv=levels(x*B)
        E0=lv[0][0]
        lst=[]
        for E,mult,name in lv[:6]:
            lst.append({'term':f"{mult}{name}",'E_over_B':round((E-E0)/B,4)})
        out.append({'Dq_over_B':x,'levels':lst})
        print(x, [(l['term'],l['E_over_B']) for l in lst], flush=True)
    json.dump(out,open('/tmp/ts/result.json','w'),indent=1)
EOF
cd /tmp/ts && time python3 ts.py