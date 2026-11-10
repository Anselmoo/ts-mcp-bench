python3 -c "
import numpy as np
from fit import spectrum
from scipy.optimize import brentq, minimize_scalar
def trip(x):
    L=spectrum(x); E0=L[0][0]
    return [E-E0 for E,d,c in L[1:] if d==3 and abs(abs(c)-1)<1e-3]
obs=np.array([13960,22740,29700.])
def f(x):
    t=trip(x); return t[1]/t[0]-obs[1]/obs[0]
x=brentq(f,1.9,2.2); t=trip(x)
# least-squares B with fixed x
B_fit=np.dot(t[:3],obs)/np.dot(t[:3],t[:3])
print('x=',x,'levels(B units)=',t[:3])
print('B from each:',obs[0]/t[0],obs[1]/t[1],obs[2]/t[2])
print('B LSQ',B_fit,'Dq=',x*B_fit)
# refine: minimize over x and B jointly
def g(p):
    x,B=p; tt=trip(x); return np.sum((B*np.array(tt[:3])-obs)**2)
r=minimize_scalar(lambda x: min(((g([x,B])) for B in [obs[0]/trip(x)[0]])),bounds=(1.9,2.2),method='bounded')
x=r.x; B=obs[0]/trip(x)[0]; print('x',x,'B',B,'Dq',x*B, 'pred', B*np.array(trip(x)[:3]))
"