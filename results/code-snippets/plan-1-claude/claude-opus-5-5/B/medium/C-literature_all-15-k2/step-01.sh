
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) * int Y*_{2m1} Y_{k,m1-m2} Y_{2m2}
    q=m1-m2
    if abs(q)>k: return 0.0
    # int Y*_{l m1} Y_{kq} Y_{l m2} = (-1)^m1 gaunt(2,k,2,-m1,q,m2)
    return float((-1)**m1*gaunt(2,k,2,-m1,q,m2))*np.sqrt(4*np.pi/(2*k+1))
C={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def g(i,j,k,l,F):  # <ij|kl>
    (mi,si),(mj,sj),(mk,sk),(ml,sl)=so[i],so[j],so[k],so[l]
    if si!=sk or sj!=sl or mi+mj!=mk+ml: return 0
    return sum(F[kk]*C[(kk,mi,mk)]*C[(kk,ml,mj)] for kk in (2,4))
def V1(i,j):
    (mi,si),(mj,sj)=so[i],so[j]
    if si!=sj: return 0
    if mi==mj: return {0:6,1:-4,-1:-4,2:1,-2:1}[mi]
    if abs(mi-mj)==4: return 5
    return 0
def build(F,Dq):
    H=np.zeros((N,N))
    # second quantization: apply a+_i a+_j a_l a_k
    def apply(ops,det):
        st=list(det); sign=1
        for typ,o in reversed(ops):
            if typ=='a':
                if o not in st: return None,0
                p=st.index(o); sign*=(-1)**p; st.pop(p)
            else:
                if o in st: return None,0
                st.insert(0,o)
                # sort
        # sort with sign
        arr=st[:]; s=1
        for a in range(len(arr)):
            for b in range(len(arr)-1-a):
                if arr[b]>arr[b+1]: arr[b],arr[b+1]=arr[b+1],arr[b]; s=-s
        return tuple(arr),sign*s
    for d in dets:
        c=idx[d]
        for i in range(10):
            for j in range(10):
                v=V1(i,j)*Dq
                if v:
                    r,s=apply([('c',i),('a',j)],d)
                    if r: H[idx[r],c]+=v*s
        for k in d:
            for l in d:
                if k==l: continue
                for i in range(10):
                    for j in range(10):
                        v=g(i,j,k,l,F)
                        if abs(v)>1e-12:
                            r,s=apply([('c',i),('c',j),('a',l),('a',k)],d)
                            if r: H[idx[r],c]+=0.5*v*s
    return H
# precompute pieces linear in params
H2=build({2:1,4:0},0);H4=build({2:0,4:1},0);HD=build({2:0,4:0},1)
# Ms and C4
Ms=np.array([sum(0.5 if so[o][1]==0 else -0.5 for o in d) for d in dets])
c4=np.array([1j**(sum(so[o][0] for o in d)%4) for d in dets])
np.save('/tmp/H.npy',np.array([H2,H4,HD]))
def levels(Dq,B,Cc):
    F2=49*B+7*Cc; F4=12.6*Cc
    H=F2*H2+F4*H4+Dq*HD
    # restrict Ms=1/2 block: quartets & doublets each appear
    sel=np.where(abs(Ms-0.5)<1e-9)[0]
    h=H[np.ix_(sel,sel)]
    w,v=np.linalg.eigh(h)
    # group
    out=[];i=0
    Ms32=np.where(abs(Ms-1.5)<1e-9)[0]
    w32=np.linalg.eigvalsh(H[np.ix_(Ms32,Ms32)])
    while i<len(w):
        j=i
        while j<len(w) and w[j]-w[i]<1e-3: j+=1
        tr=np.real(np.sum(np.conj(v[:,i:j])*(c4[sel][:,None]*v[:,i:j])))
        quart=np.any(abs(w32-w[i])<1e-3)
        out.append((w[i],j-i,round(tr),'4' if quart else '2'))
        i=j
    e0=out[0][0]
    return [(e-e0,d,t,s) for e,d,t,s in out]
import pickle
pickle.dump(None,open('/tmp/x','wb'))
def label(L):
    names=[]
    cnt={}
    for e,d,t,s in L:
        if d==3: n='T1' if t==1 else 'T2'
        elif d==1: n='A1' if t==1 else 'A2'
        elif d==2: n='E'
        else: n='?%d'%d
        key=s+n; cnt[key]=cnt.get(key,0)+1
        names.append((key+'(%d)'%cnt[key],e))
    return names
obs={'4T2(1)':8480,'4A2(1)':16305,'4T1(2)':20360,'2T1(2)':21001}
def res(p):
    nm=dict(label(levels(*p)))
    return [nm[k]-v for k,v in obs.items()]
r=least_squares(res,[800,800,3500])
print(r.x,res(r.x))
for n,e in label(levels(*r.x))[:15]: print(n,round(e))
EOF
python3 /tmp/d7.py
