import ts, numpy as np
def spec(Dq,B,CB=4.5):
    e=np.sort(ts.levels(Dq,B,CB)); g=e[0]
    lv=[]
    for v in e:
        if lv and abs(v-lv[-1][0])<1e-3: lv[-1][1]+=1
        else: lv.append([v,1])
    return [v-g for v,m in lv]
for B in [860,880,887,900,920]:
    s=spec(1060,B); print(B,[round(x) for x in s], round(s[2]+s[3]))
