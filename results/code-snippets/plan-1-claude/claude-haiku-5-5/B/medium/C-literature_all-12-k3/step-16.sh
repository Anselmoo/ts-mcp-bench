cd <SANDBOX_TMP>/w && cat > fitall2.py << 'EOF'
import numpy as np
import fast
from fast import *
from scipy.optimize import least_squares
from scipy.linalg import eigh
Sr = S2
def analyze_fast(Dq,B,C):
    H=H_of(Dq,B,C); H=0.5*(H+H.conj().T).real
    w,v=np.linalg.eigh(H+1e4*Sr)
    out=[]; i=0
    while i<len(w):
        j=i
        while j+1<len(w) and abs(w[j+1]-w[i])<1e-4*max(1,abs(w[i])): j+=1
        vs=v[:,i:j+1]
        s2=np.real(np.trace(vs.conj().T@Sr@vs))/(j-i+1)
        if abs(s2-0.75)<1e-6:
            out.append((w[i]-7500, j-i+1, np.real(np.trace(vs.conj().T@fast.Rop@vs))))
        i=j+1
    return out
Lz=np.array([sum(ms[x//2] for x in d) for d in dets])
Rop=np.diag(np.exp(-1j*np.pi/2*Lz))
fast.Rop=Rop
def model(p):
    Dq,B,C=p
    q,_=levels_fast(Dq,B,C); g0=q[0]
    vals=[]
    for v in q:
        if not vals or abs(v-vals[-1][0])>1e-2: vals.append([v,1])
        else: vals[-1][1]+=1
    qr=[(v-g0,m) for v,m in vals]
    t2=[v for v,m in qr if m==12][1]; a2=[v for v,m in qr if m==4][0]; t1p=[v for v,m in qr if m==12][2]
    dbl=analyze_fast(Dq,B,C)
    t1=[e-g0 for e,dg,tr in dbl if dg==6 and abs(tr-2)<1e-3]
    return np.array([t2,a2,t1p,t1[1]])
obs=np.array([6150.,12400.,16850.,19000.])
if __name__=="__main__":
    import time; t=time.time(); print(model((673,795,3180)), time.time()-t)
    best=None
    for Dq0 in [550,650,750]:
      for B0 in [700,850,1000]:
        for C0 in [3000,4000,4500]:
            s=least_squares(lambda p: model(p)-obs,[Dq0,B0,C0],x_scale=[100,100,300],max_nfev=100)
            if best is None or s.cost<best.cost: best=s
    print("params Dq,B,C:",best.x)
    print("model:",model(best.x)); print("resid:",model(best.x)-obs)
EOF
timeout 550 python3 fitall2.py 2>&1 | tail -6