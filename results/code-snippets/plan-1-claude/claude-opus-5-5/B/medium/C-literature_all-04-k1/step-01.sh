
cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2
# complex basis m=-2..2 ; ck coefficients
def ck(k,m1,m2):
    # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) * int Y*lm1 Ykq Ylm2
    q=m1-m2
    if abs(q)>k: return 0.0
    g=float(gaunt(l,k,l,-m1,q,m2))*(-1)**m1
    return np.sqrt(4*np.pi/(2*k+1))*g
def U(m1,m2,m3,m4,F):
    # <m1 m2|1/r|m3 m4>
    if m1+m2!=m3+m4: return 0.0
    return sum(ck(k,m1,m3)*ck(k,m4,m2)*F[k] for k in (0,2,4))
def build(Dq,B,C):
    F={0:0,2:49*B+7*C,4:63*C/5}
    F[2]=(B*49+7*C); # F2 = 49F2' ; B=F2'-5F4', C=35F4'
    F4p=C/35; F2p=B+5*F4p
    F={0:0,2:49*F2p,4:441*F4p}
    ms=[-2,-1,0,1,2]
    # crystal field in complex basis: Oh with z quaternion: V = Dq*(6 for m=0, -4 m=+-1, 1 m=+-2) + 5Dq coupling m=2,-2
    V=np.zeros((5,5))
    d={-2:1,-1:-4,0:6,1:-4,2:1}
    for i,m in enumerate(ms): V[i,i]=d[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    so=[(m,s) for m in ms for s in (0,1)]
    dets=list(itertools.combinations(range(10),3))
    idx={d:i for i,d in enumerate(dets)}
    H=np.zeros((len(dets),)*2)
    def apply1(det):
        out=[]
        for p,a in enumerate(det):
            ma,sa=so[a]
            for b in range(10):
                mb,sb=so[b]
                if sb!=sa: continue
                v=V[ms.index(mb),ms.index(ma)]
                if v==0: continue
                new=list(det); new[p]=b
                if b!=a and b in det: continue
                # sign
                lst=new; sign=1
                arr=list(lst)
                for i in range(len(arr)):
                    for j in range(len(arr)-1-i):
                        if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sign=-sign
                out.append((tuple(arr),sign*v))
        return out
    for det in dets:
        for nd,v in apply1(det): H[idx[nd],idx[det]]+=v
    # two-electron: sum over pairs
    for det in dets:
        for (p,q) in itertools.combinations(range(3),2):
            a,b=det[p],det[q]
            for c in range(10):
                for d_ in range(10):
                    if c==d_: continue
                    if (c in det and c not in (a,b)) or (d_ in det and d_ not in (a,b)): continue
                    ma,sa=so[a];mb,sb=so[b];mc,sc=so[c];md,sd=so[d_]
                    if sc!=sa or sd!=sb: continue
                    v=U(mc,md,ma,mb,F)
                    if v==0: continue
                    new=list(det); new[p]=c; new[q]=d_
                    arr=list(new); sign=1
                    for i in range(3):
                        for j in range(2-i):
                            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sign=-sign
                    if len(set(arr))<3: continue
                    H[idx[tuple(arr)],idx[det]]+=0.5*sign*v*1  # c<->d double counting handled by 0.5
    return H
def levels(Dq,B,C):
    e=np.linalg.eigvalsh(build(Dq,B,C)); e=e-e[0]
    # unique with degeneracy
    out=[];
    for x in np.round(e,2):
        if out and abs(out[-1][0]-x)<0.5: out[-1][1]+=1
        else: out.append([x,1])
    return out
print(levels(1750,610.9,3574)[:6])
print(levels(1750,610.9,0)[:4])
def f(C): 
    L=levels(1750,610.9,C); return [x for x,g in L if g==4 and x<17000][0]-14300
Cs=brentq(f,2000,5000); print(Cs, levels(1750,610.9,Cs)[:5])
EOF
python3 /tmp/d3.py
