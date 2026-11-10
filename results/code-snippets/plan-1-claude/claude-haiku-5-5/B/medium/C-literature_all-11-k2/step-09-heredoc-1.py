import numpy as np, itertools
states=list(itertools.combinations(range(10),6))
sidx={s:i for i,s in enumerate(states)}
def apply_ops(ops,state):
    occ=list(state); sign=1
    for (p,dag) in reversed(ops):
        n=sum(1 for o in occ if o<p)
        if dag:
            if p in occ: return None,0
            sign*=(-1)**n; occ.append(p); occ.sort()
        else:
            if p not in occ: return None,0
            sign*=(-1)**n; occ.remove(p)
    return tuple(occ),sign
st=states[5]; print(st, apply_ops([(0,True),(1,False)],st))
# test number op on all
print(apply_ops([(3,True),(3,False)],st))
Ms0=[j for j,s in enumerate(states) if sum(0.5 if p%2==0 else -0.5 for p in s)==0]
print(len(states),len(Ms0))
