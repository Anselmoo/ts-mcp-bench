import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=1.0;C=3003/722
Fk={0:0,2:49*B+7*C,4:63*C/5}
def c(m,mp,k):
    q=m-mp
    if abs(q)>k: return 0.0
    return float((-1)**m*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m,q,mp))
def V(a,b,cc,d):
    if a+b!=cc+d: return 0.0
    return sum(Fk[k]*c(a,cc,k)*c(d,b,k) for k in (0,2,4))
U=np.zeros((5,5),complex);s=1/np.sqrt(2)
U[4,0]=s;U[0,0]=s;U[2,1]=1;U[4,2]=-1j*s;U[0,2]=1j*s;U[3,3]=s;U[1,3]=-s;U[3,4]=1j*s;U[1,4]=1j*s
so=[(m,sp) for sp in (1,-1) for m in range(-2,3)]
def sortsign(l):
    sg=1
    for a in range(len(l)):
        for b in range(a+1,len(l)):
            if l[a]>l[b]: sg=-sg
    return sg
def ann(l,x):
    if x not in l: return None
    i=l.index(x);return l[:i]+l[i+1:],(-1)**i
def run(Dq,M):
    h=U@np.diag([6*Dq,6*Dq,-4*Dq,-4*Dq,-4*Dq]).astype(complex)@U.conj().T
    states=[x for x in itertools.combinations(range(10),3) if sum(so[i][1] for i in x)==M]
    idx={x:i for i,x in enumerate(states)};n=len(states);H=np.zeros((n,n),complex)
    for j,st in enumerate(states):
        for r in st:
            for p in range(10):
                if so[p][1]!=so[r][1]: continue
                hv=h[so[p][0]+2,so[r][0]+2]
                if abs(hv)<1e-12: continue
                l,sg=ann(list(st),r)
                if p in l: continue
                l4=[p]+l
                H[idx[tuple(sorted(l4))],j]+=hv*sg*sortsign(l4)
        for r in st:
          for s_ in st:
            if r==s_: continue
            for p in range(10):
              for q in range(10):
                if p==q or so[p][1]!=so[r][1] or so[q][1]!=so[s_][1]: continue
                v=V(so[p][0],so[q][0],so[r][0],so[s_][0])
                if abs(v)<1e-12: continue
                a1=ann(list(st),r)
                a2=ann(a1[0],s_)
                if a2 is None: continue
                l2=a2[0];sg=a1[1]*a2[1]
                if q in l2: continue
                l3=[q]+l2
                if p in l3: continue
                l4=[p]+l3
                H[idx[tuple(sorted(l4))],j]+=0.5*v*sg*sortsign(l4)
    H=(H+H.conj().T)/2
    return np.linalg.eigvalsh(H)
def clean(w):
    out=[]
    for x in w:
        if out and abs(x-out[-1][0])<1e-6: out[-1][1]+=1
        else: out.append([x,1])
    return out
for Dq in (1,2.2,3.5):
    q4=clean(run(Dq,3));d=clean(run(Dq,1))
    # Ms=1 sector here sums spins: M=1 means 2 up 1 down -> S=1/2 and 3/2
    g=d[0][0]
    print(Dq,[(round(x-g,3),n) for x,n in d[:9]])
    print(' quartets',[(round(x-g,3),n) for x,n in q4])
