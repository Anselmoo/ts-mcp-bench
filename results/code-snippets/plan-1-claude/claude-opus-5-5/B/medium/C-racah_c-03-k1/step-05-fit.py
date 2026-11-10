import numpy as np
from scipy.optimize import brentq,least_squares
m=np.load('m.npz');HV,H2,H4=m['HV'],m['H2'],m['H4']
def lev(Dq,B,C):
    e=np.linalg.eigvalsh(Dq*HV+(49*B+7*C)*H2+(441*C/35)*H4); e=e-e[0]
    u=[]
    for x in e:
        if not u or abs(x-u[-1][0])>0.1: u.append([x,1])
        else: u[-1][1]+=1
    return u
print([(round(a,1),b) for a,b in lev(1917,824,3296)[:10]])
