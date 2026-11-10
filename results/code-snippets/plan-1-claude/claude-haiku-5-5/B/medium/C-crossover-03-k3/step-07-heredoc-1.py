import numpy as np, itertools
xg, wg = np.polynomial.legendre.leggauss(14)
nphi=28
pts=[]; ws=[]
for ct, w in zip(xg, wg):
    st=np.sqrt(1-ct*ct)
    for ph in np.linspace(0,2*np.pi,nphi,endpoint=False):
        pts.append([st*np.cos(ph), st*np.sin(ph), ct]); ws.append(w*2*np.pi/nphi)
P=np.array(pts); W=np.array(ws); x,y,z=P.T
funcs=[x*y, y*z, x*z, 2*z*z-x*x-y*y, x*x-y*y]
F=np.array([f/np.sqrt(np.sum(W*f*f)) for f in funcs])
g=np.clip(P@P.T,-1,1); A=F*W
Ik={k:np.einsum('ap,cp,pq,bq,dq->acbd',A,F,np.polynomial.legendre.Legendre.basis(k)(g),A,F,optimize=True) for k in [0,2,4]}
B=1.0; C=4.0
F4=441*C/35; F2=(441*B+5*F4)/9; Fk={0:0,2:F2,4:F4}
def V(i,j,k,l):
    mi,si=divmod(i,2); mj,sj=divmod(j,2); mk,sk=divmod(k,2); ml,sl=divmod(l,2)
    if si!=sk or sj!=sl: return 0.0
    return sum(Fk[kk]*Ik[kk][mi,mk,mj,ml] for kk in [0,2,4])
def op(s, ops):
    sign=1
    for typ,o in reversed(ops):
        n=bin(s & ((1<<o)-1)).count('1')
        if typ=='a':
            if not (s>>o)&1: return None,0
            s&=~(1<<o)
        else:
            if (s>>o)&1: return None,0
            s|=(1<<o)
        if n%2: sign=-sign
    return s,sign
states=[sum(1<<o for o in occ) for occ in itertools.combinations(range(10),2)]
idx={s:n for n,s in enumerate(states)}; D=len(states)
quads=[(i,j,k,l,V(i,j,k,l)) for i,j,k,l in itertools.product(range(10),repeat=4) if i!=j and k!=l and abs(V(i,j,k,l))>1e-12]
H=np.zeros((D,D))
for s in states:
    c=idx[s]
    for i,j,k,l,v in quads:
        s1,a1=op(s,[('a',k)]); 
        if s1 is None: continue
        s2,a2=op(s1,[('a',l)]);
        if s2 is None: continue
        s3,a3=op(s2,[('c',j)])
        if s3 is None: continue
        s4,a4=op(s3,[('c',i)])
        if s4 is None: continue
        H[idx[s4],c]+=0.5*v*a1*a2*a3*a4
Sp=np.zeros((D,D)); Sz=np.zeros((D,D))
for s in states:
    c=idx[s]
    for m in range(5):
        t,sg=op(s,[('c',2*m),('a',2*m+1)])
        if t is not None: Sp[idx[t],c]+=sg
    Sz[c,c]=0.5*sum((s>>(2*m)&1)-(s>>(2*m+1)&1) for m in range(5))
S2=Sp.T@Sp+Sz@Sz+Sz
w,v=np.linalg.eigh(H); s2=np.einsum('ia,ij,ja->a',v,S2,v)
for e,s in zip(w,s2):
    print(round(e,4), round(s,3))
