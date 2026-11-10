
cd /dev/shm && cat > b.py <<'E'
from a import *
from scipy.optimize import least_squares
obs=np.array([22640,22930,25080])
def lev(Dq,B):
    w=spec(Dq,B,4.6*B);w=w-w[0]
    u=[]
    for x in w:
        if not u or x-u[-1]>1: u.append(x)
    return np.array(u)
for D in [1500,2000,2500,3000,3500]:
    print(D,np.round(lev(D,600)[:8]))
best=[]
for D0 in [1500,2000,2500,3000,3500,4000]:
  for B0 in [300,500,700,900]:
    r=least_squares(lambda p:lev(*p)[1:4]-obs,[D0,B0])
    best.append((r.cost,r.x))
best.sort(key=lambda t:t[0])
for b in best[:5]:print(b, lev(*b[1])[:6])
E
python3 b.py
