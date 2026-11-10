from d4 import *
import numpy as np
def trip_terms(Dq,B):
    t,q=levels(Dq,B,4.3*B)
    # group degeneracies
    g=[];
    for x in t:
        if g and abs(x-g[-1][0])<1e-2: g[-1][1]+=1
        else: g.append([x,1])
    return g,q
g,q=trip_terms(2500,600)
print([(round(x-g[0][0]),n) for x,n in g][:10]); print(round(q[0]-g[0][0]))
