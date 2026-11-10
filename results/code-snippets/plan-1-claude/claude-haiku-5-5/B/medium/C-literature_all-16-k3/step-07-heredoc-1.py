import numpy as np
d = np.load('/dev/shm/ang.npz'); A0,A2,A4 = d['A0'],d['A2'],d['A4']
s2 = np.sqrt(2)
nso=10; dim=2**nso
# build annihilation ops only in N=8 sector basis
states = [st for st in range(dim) if bin(st).count('1')==8]
index = {st:i for i,st in enumerate(states)}
n=len(states)
def apply_c(i, st):   # annihilate orbital i in state st -> (sign, newst) or None
    if not (st>>i)&1: return None
    sign = (-1)**bin(st & ((1<<i)-1)).count('1')
    return sign, st ^ (1<<i)
def apply_cd(i, st):
    if (st>>i)&1: return None
    sign = (-1)**bin(st & ((1<<i)-1)).count('1')
    return sign, st | (1<<i)
def op2(a,b,c,d_):  # c+_a c+_b c_d c_c acting on states (N preserved)
    M = np.zeros((n,n))
    for st in states:
        r = apply_c(c, st)
        if r is None: continue
        s1,st1 = r
        r = apply_c(d_, st1)
        if r is None: continue
        s2,st2 = r
        r = apply_cd(b, st2)
        if r is None: continue
        s3,st3 = r
        r = apply_cd(a, st3)
        if r is None: continue
        s4,st4 = r
        M[index[st4], index[st]] += s1*s2*s3*s4
    return M
def op1(a,b):
    M = np.zeros((n,n))
    for st in states:
        r = apply_c(b, st)
        if r is None: continue
        s1,st1=r
        r = apply_cd(a, st1)
        if r is None: continue
        s2,st2=r
        M[index[st2], index[st]] += s1*s2
    return M
# orbital index m+2 -> o = 0..4 ; spin-orbital = 2*o+s
def so(o,s): return 2*o+s
# one-electron cubic field
def cubic(Dq):
    v_xy = np.zeros(5,complex); v_xy[4]=1/(1j*s2); v_xy[0]=-1/(1j*s2)
    v_xz = np.zeros(5,complex); v_xz[3]=-1/s2; v_xz[1]=1/s2
    v_yz = np.zeros(5,complex); v_yz[3]=1j/s2; v_yz[1]=1j/s2
    v_z2 = np.zeros(5,complex); v_z2[2]=1
    v_x2 = np.zeros(5,complex); v_x2[4]=1/s2; v_x2[0]=1/s2
    Pt = sum(np.outer(v,v.conj()) for v in (v_xy,v_xz,v_yz))
    Pe = sum(np.outer(v,v.conj()) for v in (v_z2,v_x2))
    return -4*Dq*Pt + 6*Dq*Pe
# precompute 1-body matrices for each (a,b)
H1 = {}
for a in range(5):
    for b in range(5):
        M = np.zeros((n,n))
        for s in (0,1): M += op1(so(a,s),so(b,s))
        H1[(a,b)] = M
# two-body operators: 1/2 sum_{abcd,s,t} V c+_{a s} c+_{b t} c_{d t} c_{c s}
# V_abcd = <ab|g|cd> with spin a=c, b=d -> need V_{abcd} real
pair = {}
for a in range(5):
 for b in range(5):
  for c in range(5):
   for d in range(5):
    pair[(a,b,c,d)] = (A0[a,b,c,d], A2[a,b,c,d], A4[a,b,c,d])
# precompute the two-body ops per (a,b,c,d,s,t) lazily
cache = {}
def T(a,b,c,d,s,t):
    key=(a,b,c,d,s,t)
    if key not in cache: cache[key]=op2(so(a,s),so(b,t),so(d,t),so(c,s))
    return cache[key]
def Hee(F0,F2,F4):
    H = np.zeros((n,n))
    for a in range(5):
     for b in range(5):
      for c in range(5):
       for d in range(5):
        v = F0*pair[(a,b,c,d)][0]+F2*pair[(a,b,c,d)][1]+F4*pair[(a,b,c,d)][2]
        if abs(v)<1e-12: continue
        for s in (0,1):
         for t in (0,1):
          H += 0.5*v*T(a,b,c,d,s,t)
    return H
# Precompute Hee for F-basis: H depends linearly on F0,F2,F4 -> build three matrices
Hk = {}
Hk['F0']=Hee(1,0,0); Hk['F2']=Hee(0,1,0); Hk['F4']=Hee(0,0,1)
np.savez('/dev/shm/H.npz', F0=Hk['F0'], F2=Hk['F2'], F4=Hk['F4'], states=np.array(states))
# one-body for cubic: sum over a,b of hm[a,b]*H1 -> separate t2g/eg basis: just build total as needed
print("built")
