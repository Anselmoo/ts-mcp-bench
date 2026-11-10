
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from scipy.optimize import least_squares
from sympy.physics.wigner import gaunt
# spin orbitals: m=-2..2, s=+-1/2
orbs=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
def ck(k,m1,m2): # c^k(2m1,2m2)
    return float((-1)**m1*np.sqrt(25)*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in range(-2,3) for b in range(-2,3)}
def R(m1,m2,m3,m4,F):  # <m1 m2|1/r|m3 m4>
    if m1+m2!=m3+m4: return 0
    return sum(F[k]*CK[(k,m1,m3)]*CK[(k,m4,m2)] for k in (0,2,4))
# cubic crystal field in real-ylm: Oh: <m|V|m'> with Dq
def Vcf(Dq):
    V=np.zeros((5,5)); idx=lambda m:m+2
    V[idx(0),idx(0)]=6*Dq; V[idx(1),idx(1)]=V[idx(-1),idx(-1)]=-4*Dq
    V[idx(2),idx(2)]=V[idx(-2),idx(-2)]=Dq
    V[idx(2),idx(-2)]=V[idx(-2),idx(2)]=5*Dq
    return V
dets=list(itertools.combinations(range(10),7))
index={d:i for i,d in enumerate(dets)}
def apply2(det,p,q,r,s):  # a+_p a+_q a_s a_r
    st=list(det); sign=1
    for op,o in (('a',r),('a',s),('c',q),('c',p)):
        if op=='a':
            if o not in st: return None,0
            i=st.index(o); sign*=(-1)**i; st.pop(i)
        else:
            if o in st: return None,0
            st.insert(0,o); 
            # sort
            n=0; 
            lst=st
            # bubble count
            perm=sorted(range(len(lst)),key=lambda k:lst[k])
            # parity
            p_=list(perm); par=0
            vis=[False]*len(p_)
            for i0 in range(len(p_)):
                if not vis[i0]:
                    j=i0;L=0
                    while not vis[j]: vis[j]=True;j=p_[j];L+=1
                    par+=L-1
            sign*=(-1)**par; st=sorted(lst)
    return tuple(st),sign
def build(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5*... if False else 441*C/35
    F={0:0,2:F2/49*1.0,4:F4/441*1.0}
    # F as in Condon-Shortley F^k: F2=49F_2, using c^k with F^k
    F={0:0,2:F2,4:F4}
    V=Vcf(Dq); N=len(dets); H=np.zeros((N,N))
    for d in dets:
        i=index[d]
        for p in range(10):
            for r in range(10):
                if orbs[p][1]!=orbs[r][1]: continue
                v=V[orbs[p][0]+2,orbs[r][0]+2]
                if v==0: continue
                # a+_p a_r
                if r not in d: continue
                st=list(d); k=st.index(r); sg=(-1)**k; st.pop(k)
                if p in st: continue
                st.append(p); st2=sorted(st); k2=st2.index(p); sg*=(-1)**k2
                H[index[tuple(st2)],i]+=v*sg
        for p,q in itertools.combinations(range(10),2):
          for r,s in itertools.combinations(range(10),2):
            if r not in d or s not in d: continue
            # antisymmetrized
            def g(a,b,c,e):
                if orbs[a][1]!=orbs[c][1] or orbs[b][1]!=orbs[e][1]: return 0
                return R(orbs[a][0],orbs[b][0],orbs[c][0],orbs[e][0],F)
            val=g(p,q,r,s)-g(p,q,s,r)
            if val==0: continue
            nd,sg=apply2(d,p,q,r,s)
            if nd is None: continue
            H[index[nd],i]+=val*sg
    return H
# S^2
def S2():
    N=len(dets); M=np.zeros((N,N))
    for d in dets:
        i=index[d]; sz=sum(orbs[o][1] for o in d)
        M[i,i]+=sz*sz-sz  # S2 = S-S+ ... use S+S- + Sz^2 - Sz
        # S+S-: lower then raise
        for a in d:
            if orbs[a][1]==-0.5: continue
            b=a+1  # same m, spin down
            pass
    return None
EOF
echo ok