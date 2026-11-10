cd <SANDBOX_TMP> && cat > f.py <<'E'
import numpy as np
from a import levels
obs=np.array([7150,15200,19200,21130.]); deg=[12,4,12,6]
def clusters(e):
    out=[];i=0
    while i<len(e):
        j=i
        while j+1<len(e) and e[j+1]-e[j]<2: j+=1
        out.append((e[i:j+1].mean(),j-i+1)); i=j+1
    return out
def pred(p):
    e=levels(*p); cl=clusters(np.sort(e))
    r=[]
    for o,d in zip(obs,deg):
        c=[x for x,n in cl if n==d and x>100]
        r.append(min(c,key=lambda x:abs(x-o)))
    return np.array(r)
def res(p): return pred(p)-obs
best=None
for p0 in ([800,850,3500],[900,900,3500],[850,800,3000]):
    p=np.array(p0,float)
    for it in range(15):
        r=res(p); J=np.zeros((4,3))
        for k in range(3):
            dp=np.zeros(3);dp[k]=2;J[:,k]=(res(p+dp)-r)/2
        step=np.linalg.lstsq(J,-r,rcond=None)[0]
        p=p+step
        if abs(step).max()<0.01:break
    print(p0,p,res(p))
E
python3 f.py