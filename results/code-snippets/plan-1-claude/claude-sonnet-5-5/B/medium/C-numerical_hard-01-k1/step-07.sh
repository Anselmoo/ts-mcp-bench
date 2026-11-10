cd <SANDBOX_TMP> && cat > b.py <<'E'
from a import *
obs=[18850,19750,20560]
best=[]
for Dq in range(1500,3600,100):
  for B in range(400,1000,50):
    L=levels(B,4.7*B,Dq); g=L[0][0]
    e=[x-g for x,d in L[1:]]
    r=sum((e[i]-obs[i])**2 for i in range(3))
    best.append((r,Dq,B,[round(x) for x in e[:5]]))
best.sort()
for b in best[:6]:print(b)
E
python3 b.py