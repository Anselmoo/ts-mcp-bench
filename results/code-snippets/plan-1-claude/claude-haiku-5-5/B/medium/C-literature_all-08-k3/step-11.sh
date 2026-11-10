python3 -c "
from d5 import *
Dq,B,C=1000.,800.,3200.
w,s2=levels(Dq,B,C)
sel=np.abs(s2-15/4)<1e-6
w6=w[np.abs(s2-35/4)<1e-6]
print('sextet ground', np.round(w6,1))
q=np.sort(w[sel])
# group
g=[];cur=[q[0]]
for x in q[1:]:
    if abs(x-cur[-1])<1e-4: cur.append(x)
    else: g.append((cur[0],len(cur))); cur=[x]
g.append((cur[0],len(cur)))
for e,n in g[:8]: print(round(e-w6[0],1), n)
"