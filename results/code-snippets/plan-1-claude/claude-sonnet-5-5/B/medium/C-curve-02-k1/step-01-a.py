import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=1.0;C=3003/722
F2=49*B+7*C;F4=63*C/5;F0=0
Fk={0:F0,2:F2,4:F4}
def ck(l,m,lp,mp,k):
    # <l m|C^k_{m-mp}|l' mp>
    return float(gaunt(l,k,l,-m,m-mp,mp)*(-1)**m)*np.sqrt(5*5)/1 if False else None
# use direct: c^k(m,m')=sqrt(4pi/(2k+1))∫Y2m* Yk(m-m') Y2m'
def c(m,mp,k):
    q=m-mp
    if abs(q)>k: return 0.0
    return float((-1)**m*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m,q,mp)) 
ms=[-2,-1,0,1,2]
def V(a,b,cc,d): # <ab|1/r12|cd> orbitals m: a,b -> c,d  (a->c, b->d)
    if a+b!=cc+d: return 0.0
    s=0
    for k in (0,2,4):
        # ak = F^k * c^k(a,c) c^k(d,b)
        s+=Fk[k]*c(a,cc,k)*c(d,b,k)
    return s
# real->complex: dz2=m0; x2-y2=(2+-2)/√2 ; xy=(2-(-2))/(i√2); xz,yz
U=np.zeros((5,5),complex) # columns real orbitals in m basis index m+2
s=1/np.sqrt(2)
U[4,0]=s;U[0,0]=s            # x2-y2
U[2,1]=1                      # z2
U[4,2]=-1j*s;U[0,2]=1j*s     # xy
U[3,3]=s;U[1,3]=-s            # xz
U[3,4]=1j*s;U[1,4]=1j*s       # yz
eg=[0,1];t=[2,3,4]
def run(Dq):
    d=np.diag([6*Dq,6*Dq,-4*Dq,-4*Dq,-4*Dq]).astype(complex)
    h=U@d@U.conj().T
    so=[(m,s) for s in (1,-1) for m in range(-2,3)]
    states=[x for x in itertools.combinations(range(10),3) if sum(so[i][1] for i in x)==1]
    idx={x:i for i,x in enumerate(states)}
    n=len(states);H=np.zeros((n,n),complex)
    # build via second quantization
    def apply(st,ops):
        # ops list of (create idx, annih idx) sequence: a†_p a†_q a_s a_r
        pass
    for j,st in enumerate(states):
        # one-body
        for r in st:
            for p in range(10):
                if so[p][1]!=so[r][1]: continue
                hv=h[so[p][0]+2,so[r][0]+2]
                if abs(hv)<1e-12: continue
                l=list(st);pos=l.index(r);rest=l[:pos]+l[pos+1:]
                if p in rest: continue
                new=rest[:];# insert p
                new=[p]+rest  # p at front after annihilating r at pos: sign (-1)^pos
                sg=(-1)**pos
                # sort
                perm=sorted(range(3),key=lambda i:new[i]);
                # sign of sorting
                arr=new[:];sgn=1
                for a in range(3):
                    for b in range(a+1,3):
                        if arr[a]>arr[b]: sgn=-sgn
                key=tuple(sorted(new))
                H[idx[key],j]+=hv*sg*sgn
        # two-body 1/2 sum <pq|rs'> a†p a†q a_s a_r ; V(a,b,c,d)=<ab|cd>
        for r in st:
          for s_ in st:
            if r==s_: continue
            for p in range(10):
              for q in range(10):
                if p==q: continue
                if so[p][1]!=so[r][1] or so[q][1]!=so[s_][1]: continue
                v=V(so[p][0],so[q][0],so[r][0],so[s_][0])
                if abs(v)<1e-12: continue
                l=list(st)
                # a_r then a_s: apply a_s first? operator a†p a†q a_s a_r : a_r first
                def ann(l,x):
                    if x not in l: return None
                    i=l.index(x);return l[:i]+l[i+1:],(-1)**i
                a1=ann(l,r)
                if a1 is None: continue
                a2=ann(a1[0],s_)
                if a2 is None: continue
                l2,sg2=a2;sg=a1[1]*sg2
                if q in l2: continue
                l3=[q]+l2;sg*=1
                if p in l3: continue
                l4=[p]+l3
                arr=l4;sgn=1
                for a in range(3):
                    for b in range(a+1,3):
                        if arr[a]>arr[b]: sgn=-sgn
                H[idx[tuple(sorted(l4))],j]+=0.5*v*sg*sgn
    H=(H+H.conj().T)/2
    # S^2 not needed: classify by degeneracy and multiplicity via Ms=3/2 energies
    w=np.linalg.eigvalsh(H)
    return w
def clean(w):
    out=[];
    for x in w:
        if out and abs(x-out[-1][0])<1e-6: out[-1][1]+=1
        else: out.append([x,1])
    return out
def q(Dq):
    # quartet energies via Ms=3/2 would need other sector; approximate by hand below
    return clean(run(Dq))
for Dq in (1,2.2,3.5):
    r=q(Dq);g=r[0][0]
    print(Dq,[(round(x-g,3),n) for x,n in r[:8]])
