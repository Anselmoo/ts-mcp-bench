
cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
ml=[-2,-1,0,1,2]; so=[(m,s) for m in ml for s in (0,1)]
def ck(k,m1,m2): # c^k(l=2 m1, l=2 m2)
    return float((-1)**m1*5*gaunt(2,k,2,-m1,m1-m2,m2)*np.sqrt(4*np.pi/(2*k+1)))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ml for b in ml}
def Fk(B,C): A=0;F2=49*B+7*C;F4=63*C/5;return {0:0,2:F2,4:F4}
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def V(a,b,c,d,F):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[a],so[b],so[c],so[d]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0
    return sum(F[k]*CK[(k,m1,m3)]*CK[(k,m4,m2)] for k in (2,4))
# cubic crystal field in |m> basis: octahedral
def hcf(Dq):
    h=np.zeros((5,5)); 
    h[2,2]=6*Dq; h[1,1]=h[3,3]=-4*Dq; h[0,0]=h[4,4]=Dq; h[0,4]=h[4,0]=5*Dq
    return h
def H(Dq,B,C):
    F=Fk(B,C); n=len(dets); M=np.zeros((n,n)); h=hcf(Dq)
    for i,d in enumerate(dets):
        for j,e in enumerate(dets):
            # one body
            pass
    # use second quantization brute
    def apply(ops,det):
        det=list(det);sign=1
        for op,o in reversed(ops):
            if op=='a':
                if o not in det: return None,0
                p=det.index(o); sign*=(-1)**p; det.pop(p)
            else:
                if o in det: return None,0
                det.insert(0,o); sign*=1
                srt=sorted(det); # permutation sign
                p=srt.index(o); sign*=(-1)**p; det=srt
        return tuple(det),sign
    for j,e in enumerate(dets):
        for a in range(10):
            for b in range(10):
                if so[a][1]!=so[b][1]: continue
                t=h[so[a][0]+2,so[b][0]+2]
                if t==0: continue
                d,s=apply([('c',a),('a',b)],e)
                if d: M[idx[d],j]+=s*t
        for a in range(10):
         for b in range(10):
          for c in range(10):
           for dd in range(10):
            v=V(a,b,c,dd,F)
            if v==0: continue
            d,s=apply([('c',a),('c',b),('a',dd),('a',c)],e)
            if d: M[idx[d],j]+=0.5*s*v
    return M
def levels(Dq,B,C):
    w=np.linalg.eigvalsh(H(Dq,B,C)); w=w-w[0]
    vals=np.round(w,1); u=[]
    for x in vals:
        if not u or abs(x-u[-1][0])>0.5: u.append([x,1])
        else: u[-1][1]+=1
    return u
Dq=1449;B=8990/15
print(levels(Dq,B,3000)[:8])
f=lambda C: levels(Dq,B,C)[1][0]-12710
C=brentq(f,2000,4000,xtol=0.5);print(C,levels(Dq,B,C)[:8])
EOF
python3 /tmp/d3.py
