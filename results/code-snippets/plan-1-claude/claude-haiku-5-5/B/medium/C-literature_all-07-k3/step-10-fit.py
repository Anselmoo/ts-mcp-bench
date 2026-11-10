import numpy as np
from scipy.optimize import least_squares
from run2 import classify
obs=np.array([19240.,21890.,23000.])
def levels(p):
    Dq,B,C=p
    out=classify(Dq,B,C)
    # group distinct levels with multiplicity
    e=np.array([x[0] for x in out]); 
    vals=[]; 
    for x in sorted(e):
        if vals and abs(x-vals[-1][0])<1e-6: vals[-1][1]+=1
        else: vals.append([x,1])
    return vals
# compute in cm-1 for given params (scale: classify uses units given)
def pattern(p):
    return levels(p)
best=[]
rng=np.random.default_rng(0)
for trial in range(300):
    Dq=rng.uniform(500,1500); B=rng.uniform(500,1100); C=rng.uniform(2.5,5)*B
    # level energies as functions; fit by choosing the three observed as the three quartet states with multiplicities (3,3,2) from ordering
    def res(p):
        Dq,B,C=p
        vals=levels((Dq,B,C))
        # use lowest three non-zero level values with multiplicity in order: T,T,E assumed -> pick levels by index
        return np.array([0,0,0])
    break
print("ok")
