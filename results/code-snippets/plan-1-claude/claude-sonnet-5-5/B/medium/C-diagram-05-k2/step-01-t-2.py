import json
for Dq,out in res:
    e0=out[0][0]
    names={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}
    print(Dq,[(f"{m}{names.get((o,c),(o,c))}",round((e-e0)/B,3)) for e,m,o,c in out[:9]])
