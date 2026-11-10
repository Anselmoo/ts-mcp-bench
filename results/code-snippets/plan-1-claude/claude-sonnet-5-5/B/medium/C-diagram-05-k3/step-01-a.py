import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=859.;C=3660.
b=1.;c=C/B
F2=49*b+7*c;F4=63*c/5
F={0:0,2:F2,4:F4}
l=2;ms=range(-2,3)
def ck(m,mp,k):
    q=m-mp
    if abs(q)>k: return 0.
    return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,q,mp))
cc={(k,m,mp):ck(m,mp,k) for k in (0,2,4) for m in ms for mp in ms}
g=np.zeros((5,)*4)
for a,m1 in enumerate(ms):
 for bb,m2 in enumerate(ms):
  for cx,m3 in enumerate(ms):
   for d,m4 in enumerate(ms):
    if m1+m2==m3+m4:
     g[a,bb,cx,d]=sum(cc[(k,m1,m3)]*cc[(k,m4,m2)]*F[k] for k in (2,4))
# real orbitals: order z2,xz,yz,x2-y2,xy ; complex idx m=-2..2
s=1/np.sqrt(2);T=np.zeros((5,5),complex)
idx=lambda m:m+2
T[0,idx(0)]=1
T[1,idx(-1)]=s;T[1,idx(1)]=-s
T[2,idx(-1)]=1j*s;T[2,idx(1)]=1j*s
T[3,idx(2)]=s;T[3,idx(-2)]=s
T[4,idx(2)]=-1j*s;T[4,idx(-2)]=1j*s
gr=np.einsum('ia,jb,kc,ld,abcd->ijkl',T.conj(),T.conj(),T,T,g)
print('imag',abs(gr.imag).max()); gr=gr.real
def Hs(Dq):
    V=np.zeros((5,5));V[2,2]=6*Dq;V[1,1]=V[3,3]=V[0,0]=0
    Vc=np.diag([Dq,-4*Dq,6*Dq,-4*Dq,Dq]).astype(complex);Vc[0,4]=Vc[4,0]=5*Dq
    return (T.conj()@Vc@T.T).real  # <i|V|j>
# check diag
print(np.round(Hs(1.),3))
Rz=np.zeros((5,5));Rz[0,0]=1;Rz[2,1]=1;Rz[1,2]=-1;Rz[3,3]=-1;Rz[4,4]=-1  # col j -> image
R3=np.zeros((5,5))
# basis z2,xz,yz,x2-y2,xy ; x->y->z->x: xy->yz, yz->zx, zx->xy
R3[2,4]=1;R3[1,2]=1;R3[4,1]=1
R3[0,0]=-.5;R3[3,0]=np.sqrt(3)/2;R3[0,3]=-np.sqrt(3)/2;R3[3,3]=-.5
# spin orbitals: p=orb+5*spin
def dets(nu,nd):
    out=[]
    for u in itertools.combinations(range(5),nu):
        for d in itertools.combinations(range(5),nd):
            out.append(tuple(u)+tuple(5+x for x in d))
    return out
def apply_ops(det,ops):pass
def build(Dq,nu,nd):
    D=dets(nu,nd);ix={d:i for i,d in enumerate(D)};n=len(D)
    h=Hs(Dq)
    H=np.zeros((n,n))
    def ann(det,p):
        if p not in det:return None
        i=det.index(p);return (-1)**i,tuple(x for x in det if x!=p)
    def cre(det,p):
        if p in det:return None
        i=sum(1 for x in det if x<p);return (-1)**i,tuple(sorted(det+(p,)))
    for j,d in enumerate(D):
        # one-body
        for q in range(10):
            r=ann(d,q)
            if not r:continue
            s1,d1=r
            for p in range(10):
                if p//5!=q//5:continue
                hv=h[p%5,q%5]
                if hv==0:continue
                r2=cre(d1,p)
                if not r2:continue
                H[ix[r2[1]],j]+=hv*s1*r2[0]
        # two-body 1/2 sum <pq|g|rs> a+p a+q a_s a_r
        for r_ in d:
            for s_ in d:
                if r_==s_:continue
                x1=ann(d,r_);x2=ann(x1[1],s_) if x1 else None
                # a_s a_r |d>: first r then s
                sg=x1[0]*x2[0];d2=x2[1]
                for p in range(10):
                    for q in range(10):
                        if p//5!=r_//5 or q//5!=s_//5:continue
                        v=gr[p%5,q%5,r_%5,s_%5]
                        if v==0:continue
                        y1=cre(d2,q)
                        if not y1:continue
                        y2=cre(y1[1],p)
                        if not y2:continue
                        H[ix[y2[1]],j]+=0.5*v*sg*y1[0]*y2[0]
    def rep(Rm):
        M=np.zeros((n,n))
        for i,a in enumerate(D):
            for j,bq in enumerate(D):
                if any((x//5)!=(y//5) for x,y in zip(sorted(a,key=lambda t:t//5),sorted(bq,key=lambda t:t//5)) ) : pass
                ua=[x for x in a if x<5];da=[x-5 for x in a if x>=5]
                ub=[x for x in bq if x<5];db=[x-5 for x in bq if x>=5]
                M[i,j]=np.linalg.det(Rm[np.ix_(ua,ub)])*np.linalg.det(Rm[np.ix_(da,db)])
        return M
    return H,rep(Rz),rep(R3)
chi={'A1':(1,1,1,1),'A2':(1,1,1,-1),'E':(2,-1,2,0),'T1':(3,0,-1,1),'T2':(3,0,-1,-1)}
# classes: E,C3(8),C2(3),C4(6)
cnt=(1,8,3,6)
def levels(Dq,nu,nd):
    H,M4,M3=build(Dq,nu,nd)
    if Dq>0 or True:
        assert abs(M4@H-H@M4).max()<1e-8*max(1,abs(H).max()),abs(M4@H-H@M4).max()
        assert abs(M3@H-H@M3).max()<1e-8*max(1,abs(H).max()),abs(M3@H-H@M3).max()
    H=(H+H.T)/2
    w,v=np.linalg.eigh(H)
    out=[];i=0
    while i<len(w):
        j=i
        while j+1<len(w) and w[j+1]-w[i]<1e-6:j+=1
        P=v[:,i:j+1]
        t=[j-i+1,np.trace(P.T@M3@P),np.trace(P.T@M4@M4@P),np.trace(P.T@M4@P)]
        for k,ch in chi.items():
            m=sum(cnt[a]*t[a]*ch[a] for a in range(4))/24
            m=round(m)
            for _ in range(m):out.append((w[i],k))
        i=j+1
    return out
def lv(Dq):
    q=levels(Dq,5,2);d=levels(Dq,4,3)
    dd=list(d)
    for e,k in q:
        for t,(e2,k2) in enumerate(dd):
            if k2==k and abs(e2-e)<1e-6:dd.pop(t);break
        else: raise Exception('nomatch')
    res=[(e,'4'+k) for e,k in q]+[(e,'2'+k) for e,k in dd]
    res.sort()
    e0=res[0][0]
    return [(e-e0,k) for e,k in res]
if __name__=='__main__':
    L=lv(0.);print(L[:8],len(L))
    import json
    out=[]
    for x in np.arange(0,4.01,.5):
        L=lv(x);out.append((x,L));print(x,[(round(e,3),k) for e,k in L[:6]])
    import pickle;pickle.dump(out,open('o.pk','wb'))
