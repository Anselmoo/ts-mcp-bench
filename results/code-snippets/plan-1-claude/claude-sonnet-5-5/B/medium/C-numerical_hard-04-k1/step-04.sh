mkdir -p ~/w && cd ~/w && cat > a.py <<'E'
import numpy as np, itertools
from math import factorial as f, sqrt
def w3j(j1,j2,j3,m1,m2,m3):
    if m1+m2+m3!=0: return 0
    if j3>j1+j2 or j3<abs(j1-j2) or abs(m1)>j1 or abs(m2)>j2 or abs(m3)>j3: return 0
    t=lambda x:f(int(round(x)))
    pre=(-1)**int(j1-j2-m3)*sqrt(t(j1+j2-j3)*t(j1-j2+j3)*t(-j1+j2+j3)/t(j1+j2+j3+1))
    pre*=sqrt(t(j1+m1)*t(j1-m1)*t(j2+m2)*t(j2-m2)*t(j3+m3)*t(j3-m3))
    s=0
    for k in range(0,40):
        a=[k,j1+j2-j3-k,j1-m1-k,j2+m2-k,j3-j2+m1+k,j3-j1-m2+k]
        if min(a)<0: continue
        s+=(-1)**k/np.prod([t(x) for x in a])
    return pre*s
def ck(k,m,mp):
    return (-1)**m*5*w3j(2,k,2,0,0,0)*w3j(2,k,2,-m,m-mp,mp)
ms=[-2,-1,0,1,2]
dets=[c for c in itertools.combinations(range(10),5) if sum(o%2 for o in c)==2]
idx={d:i for i,d in enumerate(dets)}
def apply(op,d):
    l=list(d);sg=1
    for t,o in reversed(op):
        if t=='a':
            if o not in l: return 0,None
            p=l.index(o);sg*=(-1)**p;l.pop(p)
        else:
            if o in l: return 0,None
            p=sum(1 for x in l if x<o);sg*=(-1)**p;l.insert(p,o)
    return sg,tuple(l)
# precompute operator lists
P=np.zeros((5,5));P[2,2]=1
e=np.zeros(5);e[0]=e[4]=1/sqrt(2);P+=np.outer(e,e)
n=len(dets)
def mat(ops_coef):
    M=np.zeros((n,n))
    for coef,op in ops_coef:
        for j,d in enumerate(dets):
            sg,nd=apply(op,d)
            if sg: M[idx[nd],j]+=coef*sg
    return M
Hpe=mat([(1,[('c',2*a+s),('a',2*a+s)]) for a in range(5) for s in (0,1)])  # unused
Hn_t=np.zeros((n,n));Hn_P=np.zeros((n,n))
Hn_t=mat([(1,[('c',2*a+s),('a',2*a+s)]) for a in range(5) for s in (0,1)])
Hn_P=mat([(P[a,b],[('c',2*a+s),('a',2*b+s)]) for a in range(5) for b in range(5) for s in (0,1) if P[a,b]!=0])
# Coulomb parts per k
V={}
for k in (2,4):
    ol=[]
    for m1 in ms:
     for m2 in ms:
      for m3 in ms:
       m4=m1+m2-m3
       if abs(m4)>2: continue
       v=ck(k,m1,m3)*ck(k,m4,m2)
       if abs(v)<1e-12: continue
       for s1 in (0,1):
        for s2 in (0,1):
         ol.append((0.5*v,[('c',2*(m1+2)+s1),('c',2*(m2+2)+s2),('a',2*(m4+2)+s2),('a',2*(m3+2)+s1)]))
    V[k]=mat(ol)
# S^2
Sp=lambda: None
def S2mat():
    ol=[]
    # S-S+ : sum a†(m',dn)a(m',up) a†(m,up)a(m,dn) ; up=1? orbital index 2m+s, s=1 up
    ol=[(1,[('c',2*a+0),('a',2*a+1),('c',2*b+1),('a',2*b+0)]) for a in range(5) for b in range(5)]
    M=mat(ol)
    return M+ (0.5**2+0.5)*np.eye(n)
S2=S2mat()
np.save('S2.npy',S2)
def levels(Dq,B,C):
    F4=C/35;F2=B+5*F4
    H=-4*Dq*Hn_t+10*Dq*Hn_P+49*F2*V[2]+441*F4*V[4]
    H=H+1e5*(S2-0.75*np.eye(n))
    w=np.linalg.eigvalsh((H+H.T)/2)
    return w
def exc(Dq,B,C=None):
    C=C or 4.4*B
    w=levels(Dq,B,C); w=w[w<5e4]  # doublets only
    w=w-w[0]
    # group
    gr=[];
    for x in w:
        if gr and abs(x-gr[-1][0])<1e-3: gr[-1][1]+=1
        else: gr.append([x,1])
    return gr
if __name__=="__main__":
    print(np.allclose(S2,S2.T), len(dets))
    g=exc(3000,600)
    print(g[:8])
E
python3 a.py