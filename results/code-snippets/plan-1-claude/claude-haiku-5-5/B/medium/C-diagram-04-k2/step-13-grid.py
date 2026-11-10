from run_d6 import *
import json
res={}
for dq in np.arange(0,4.01,0.5):
    lv=levels(float(dq))
    e0=lv[0][0]
    six=[(round(float(e-e0),4), f"{S*0+ (2*S+1)}{n}") for e,S,n in lv[:6]]
    res[round(float(dq),2)]=[(round(float(e-e0),4),S,n) for e,S,n in lv[:6]]
    print(round(float(dq),2), [(round(float(e-e0),4), f"{2*S+1}{n}") for e,S,n in lv[:8]], flush=True)
json.dump({str(k):v for k,v in res.items()},open('grid.json','w'))
