from d3 import *
from scipy.optimize import least_squares
def spec(Dq,B):
    e=np.sort(np.linalg.eigvalsh(build(49*B,0.0,-Dq)))
    g=e[0]; ex=e[e>g+1e-6]
    # unique triplets
    levs=[]
    for x in ex:
        if not levs or abs(x-levs[-1])>1e-6: levs.append(x)
    return [l-g for l in levs]
obs=np.array([4330,7520,18640.])
print(spec(433,600))
def res(p):
    Dq,B=p
    s=spec(Dq,B)
    return np.array(s[:3])-obs
for guess in [(433,800),(500,700),(400,900)]:
    r=least_squares(res,guess)
    print(r.x, r.fun, spec(*r.x))
