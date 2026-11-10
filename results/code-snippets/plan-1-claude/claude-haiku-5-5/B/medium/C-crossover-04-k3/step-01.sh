
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from scipy.optimize import brentq
from scipy.special import sph_harm
# orbitals: complex m=-2..2 (l=2), spin up/down -> 10 spin-orbitals
ms=[-2,-1,0,1,2]
so=[(m,s) for s in (1,-1) for m in ms]   # index
N=len(so)
# angular integrals via quadrature
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.full(nph,2*np.pi/nph))
def Y(l,m): return sph_harm(m,l,PH,TH)   # scipy: sph_harm(m,n,azimuth,polar)
Yd={m:Y(2,m) for m in ms}
def ang(k,q,m1,m3):
    # <Y_2m1|Y_kq^*|Y_2m3>
    Ykq=sph_harm(q,k,PH,TH) if abs(q)<=k else None
    return np.sum(W*np.conj(Yd[m1])*np.conj(Ykq)*Yd[m3])
def gaunt_k(k,m1,m3,m2,m4):
    tot=0
    for q in range(-k,k+1):
        Ykq=sph_harm(q,k,PH,TH)
        a=np.sum(W*np.conj(Yd[m1])*np.conj(Ykq)*Yd[m3])  # <m1|Y*_kq|m3>
        # <m2|Y_kq|m4>
        b=np.sum(W*np.conj(Yd[m2])*Ykq*Yd[m4])
        tot+=a*b
    return tot*4*np.pi/(2*k+1)
def build(Dq,B,C):
    F4=441*C/35.0
    F2=(441*B+5*F4)/9.0
    F={0:None,2:F2,4:F4}
    # one-electron cubic field in complex basis
    h=np.zeros((5,5),complex)
    idx={m:i for i,m in enumerate(ms)}
    eg=[]; t2=[]
    v=np.zeros(5,complex); v[idx[0]]=1; eg.append(v)
    v=np.zeros(5,complex); v[idx[2]]=1/np.sqrt(2); v[idx[-2]]=1/np.sqrt(2); eg.append(v)
    v=np.zeros(5,complex); v[idx[2]]=1/(1j*np.sqrt(2)); v[idx[-2]]=-1/(1j*np.sqrt(2)); t2.append(v)
    v=np.zeros(5,complex); v[idx[1]]=1/np.sqrt(2); v[idx[-1]]=1/np.sqrt(2); t2.append(v)
    v=np.zeros(5,complex); v[idx[1]]=1/(1j*np.sqrt(2)); v[idx[-1]]=-1/(1j*np.sqrt(2)); t2.append(v)
    for e in eg: h+=6*Dq*np.outer(e,e.conj())
    for t in t2: h+=-4*Dq*np.outer(t,t.conj())
    # two-electron <ab|1/r12|cd> with a=(m1), b=(m2), c=(m3), d=(m4) orbital indices
    V=np.zeros((5,5,5,5),complex)
    for i1,m1 in enumerate(ms):
     for i2,m2 in enumerate(ms):
      for i3,m3 in enumerate(ms):
       for i4,m4 in enumerate(ms):
        if m1+m2!=m3+m4: continue
        s=0
        for k in (0,2,4):
            s+=F[k]*gaunt_k(k,m1,m3,m2,m4) if k>0 else 0
        # F0 term: k=0 gives delta, F0 irrelevant for differences; set F0=0
        V[i1,i2,i3,i4]=s
    # Fock basis: 10 spin-orbitals, states = 7-element subsets
    states=list(itertools.combinations(range(N),7))
    sidx={s:i for i,s in enumerate(states)}
    D=len(states)
    H=np.zeros((D,D),complex)
    def orb(i): return so[i]
    def spo(i):  # spin-orbital index -> (orbital index in ms, spin)
        m,s=so[i]; return ms.index(m), s
    def apply_cdag_c(i,j,occ):
        # c_i^dag c_j on occupation tuple (sorted); return (sign,newocc) or None
        occ=list(occ)
        if j not in occ: return None
        sign=1
        p=occ.index(j); sign*=(-1)**p; occ.pop(p)
        if i in occ: return None
        # insert i
        q=sum(1 for x in occ if x<i); sign*=(-1)**q
        occ.insert(q,i)
        return sign,tuple(occ)
    # one-body
    for a in range(N):
        for b in range(N):
            ia,sa=spo(a); ib,sb=spo(b)
            if sa!=sb: continue
            if abs(h[ia,ib])<1e-14: continue
            for st in states:
                r=apply_cdag_c(a,b,st)
                if r is None: continue
                sg,new=r
                H[sidx[new],sidx[st]]+=sg*h[ia,ib]
    # two-body: 1/2 sum V_abcd c_a^+ c_b^+ c_d c_c  with V=<ab|1/r|cd>
    for st in states:
        occ=list(st)
        for c in occ:
            for d in occ:
                if d==c: continue
                ic,sc=spo(c); id_,sd=spo(d)
                for a in range(N):
                    for b in range(N):
                        if a==b: continue
                        ia,sa=spo(a); ib,sb=spo(b)
                        val=V[ia,ib,ic,id_]
                        if abs(val)<1e-14: continue
                        if sa==sc and sb==sd or False: pass
                        # <ab|1/r|cd> with spin: delta(sa,sc) delta(sb,sd)
                        if sa!=sc or sb!=sd: continue
                        # apply c_a^+ c_b^+ c_d c_c (c_c first)
                        r1=apply_cdag_c(c,c,st) if False else None
                        # manual: c_c acts first, then c_d, then c_b^+, then c_a^+
                        o=list(st); sign=1
                        # c_c
                        if c not in o: continue
                        p=o.index(c); sign*=(-1)**p; o.pop(p)
                        if d in o: continue
                        q=sum(1 for x in o if x<d); sign*=(-1)**q; o.insert(q,d)
                        # wait c_d applied after c_c: need d annihilated; d currently occupied in st, but after removing c, we annihilate d
                        # redo properly below
                        pass
    return None
EOF
echo draft