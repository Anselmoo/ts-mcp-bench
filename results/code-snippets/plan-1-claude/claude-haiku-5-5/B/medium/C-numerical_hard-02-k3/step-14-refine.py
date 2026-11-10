import numpy as np
from scipy.optimize import brentq, minimize_scalar
exec(open('fit.py').read().split('from scipy')[0].replace('for x in np.arange(2.6','for x in []: #'))
obs=np.array([22900,23730,24580.])
def E(x):
    L=trip_levels(x); e0=L[0][0]
    d={}
    return [ (v-e0,dg,c) for v,dg,c in L]
def get(x):
    L=E(x)
    eg=[v for v,dg,c in L if dg==6 and abs(c)<1e-3][0]
    t1=[v for v,dg,c in L if dg==9 and c>2][0]
    t2=[v for v,dg,c in L if dg==9 and c<-2][0]
    return np.array([eg,t1,t2])
def resid(x):
    Es=get(x); B=np.dot(Es,obs)/np.dot(Es,Es)
    return np.sqrt(np.mean((B*Es-obs)**2))
r=minimize_scalar(resid,bounds=(3.3,3.5),method='bounded',options={'xatol':1e-7})
x=r.x; Es=get(x); B=np.dot(Es,obs)/np.dot(Es,Es)
print('x=',x,'B=',B,'C=',4.3*B,'Dq=',x*B,'resid',resid(x))
print('levels (B units):',Es, 'calc:',B*Es)
