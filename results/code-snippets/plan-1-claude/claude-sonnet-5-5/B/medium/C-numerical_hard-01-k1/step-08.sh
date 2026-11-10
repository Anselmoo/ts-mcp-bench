cd <SANDBOX_TMP> && cat > c.py <<'E'
from a import *
obs=[18850,19750,20560]
def r(Dq,B):
    L=levels(B,4.7*B,Dq); g=L[0][0]
    e=[x-g for x,d in L[1:]]
    return sum((e[i]-obs[i])**2 for i in range(3)),e[:4],[d for x,d in L[1:5]]
best=[]
for Dq in range(2100,2320,20):
  for B in range(780,900,10):
    best.append((r(Dq,B),Dq,B))
best.sort(key=lambda x:x[0][0])
for b in best[:5]:print(b)
E
python3 c.py