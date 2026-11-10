from scipy.optimize import minimize
f=lambda x: sum(r*r for r in res2(x))
s=minimize(f,[600,780,3100],method='Nelder-Mead',options={'xatol':0.01,'fatol':1e-4,'maxiter':4000});print(s.x,res2(s.x),levels(*s.x)[:6])
