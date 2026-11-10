cd <SANDBOX_TMP> && cat > b.py <<'E'
from a import *
obs=np.array([13960,22740,29700])
best=[]
for Dq in range(1000,2001,200):
  for B in range(200,801,150):
    l=[x[0] for x in levels(singlets(Dq,B,4.5*B),3)]
    best.append((np.sum((np.array(l)-obs)**2)**.5,Dq,B,l))
best.sort(key=lambda t:t[0])
for b in best[:6]: print(b)
E
timeout 550 python3 b.py