cat > fit.py <<'EOF'
from d4 import H
import numpy as np
M={}
for ms in (2,4):
    M[ms]=[H(1,0,0,ms),H(0,1,0,ms),H(0,0,1,ms)]
def lev(Dq,B,C):
    e1=list(np.linalg.eigvalsh(Dq*M[2][0]+B*M[2][1]+C*M[2][2]))
    e2=np.linalg.eigvalsh(Dq*M[4][0]+B*M[4][1]+C*M[4][2])
    for x in e2:
        i=int(np.argmin(np.abs(np.array(e1)-x))); e1.pop(i)
    t=sorted(e1); g=[]
    for x in t:
        if g and abs(x-g[-1][0])<1e-3: g[-1][1]+=1
        else: g.append([x,1])
    return [(x-g[0][0],n) for x,n in g], e2[0]-g[0][0]
print([(round(x),n) for x,n in lev(0,600,2580)[0]])
obs=np.array([22900,23730,24580])
best=[]
for Dq in np.arange(1500,4001,25):
  for B in np.arange(200,1201,10):
    g,q=lev(Dq,B,4.3*B)
    e=np.array([x for x,n in g[1:4]])
    best.append((np.sum((e-obs)**2),Dq,B,[(round(x),n) for x,n in g[:6]],round(q)))
best.sort(key=lambda z:z[0])
for b in best[:8]: print(b)
EOF
timeout 110 python3 fit.py