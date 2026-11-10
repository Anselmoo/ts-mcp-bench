python3 - << 'EOF' 2>/dev/null | grep -v -E "unit|scaled"
import ts, numpy as np
def spec(Dq,B,CB):
    e=np.sort(ts.levels(Dq,B,CB)); g=e[0]
    lv=[]
    for v in e:
        if lv and abs(v-lv[-1][0])<1e-3: lv[-1][1]+=1
        else: lv.append([v,1])
    return [round(v-g) for v,m in lv]
for CB in [3,4.5,6]:
    print(CB, spec(1060,887,CB))
# least squares grid
best=None
for Dq in np.arange(1000,1121,2):
  for B in np.arange(700,1101,2):
    s=spec(Dq,B,4.5)
    r=(s[1]-10600)**2+(s[2]-17500)**2+(s[3]-27600)**2
    if best is None or r<best[0]: best=(r,Dq,B,s)
print(best)
EOF