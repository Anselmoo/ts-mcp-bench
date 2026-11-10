exec(open('fit.py').read().split('# scan over ratio')[0])
from scipy.optimize import brentq
def resid(x):
    ex=excited(x,1.0)
    f=np.array([ex[i][0] for i in (0,1,2)])
    Bs=np.dot(f,obs)/np.dot(f,f)
    return np.sqrt(np.mean((Bs*f-obs)**2)), Bs, f
xs=np.linspace(3.08,3.12,401)
r=[resid(x) for x in xs]
i=int(np.argmin([q[0] for q in r]))
x=xs[i]; res,Bs,f=r[i]
print("x=Dq/B",x,"B",Bs,"Dq",x*Bs,"rms",res)
print("model energies (per B):",f, "-> cm-1", Bs*f)
ex=excited(x,1.0)
for v,d in ex[:5]: print(round(v,4),d)
