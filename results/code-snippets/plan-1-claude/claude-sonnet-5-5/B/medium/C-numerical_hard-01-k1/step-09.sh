cd <SANDBOX_TMP> && cat > d.py <<'E'
from c import r
import itertools
best=None
for Dq in [2000+10*i for i in range(0,40)]:
  for B in [600+10*i for i in range(0,40)]:
    v=r(Dq,B)[0]
    if best is None or v<best[0]: best=(v,Dq,B)
print(best)
v,D0,B0=best
for Dq in [D0-10+2*i for i in range(11)]:
  for B in [B0-10+2*i for i in range(11)]:
    v=r(Dq,B)
    if v[0]<best[0]: best=(v[0],Dq,B,v[1])
print(best)
E
python3 d.py 2>&1 | tail -2