cd <SANDBOX_TMP>; cat > h.py <<'E'
from f import *
best=[]
for Dq in range(800,1300,50):
  for B in range(700,1100,50):
    r=res((B,3800,Dq))[:3]
    best.append((sum(x*x for x in r)**.5,B,Dq,[round(x) for x in r]))
best.sort();print(best[:6])
E
python3 h.py 2>&1|tail -2