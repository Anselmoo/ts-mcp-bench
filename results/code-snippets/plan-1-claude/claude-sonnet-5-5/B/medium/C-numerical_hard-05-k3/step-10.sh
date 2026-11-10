cd <SANDBOX_TMP> && cat > t.py <<'E'
from a import *
e=spectrum(0,1000,4000,3,3); e=e-e[0]
out=[]
for x in e:
  if not out or x-out[-1][0]>1: out.append([round(x),1])
  else: out[-1][1]+=1
print(out)
E
python3 t.py