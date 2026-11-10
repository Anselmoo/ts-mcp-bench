print("pairs")
def res2(p):
    Dq,B=p; s=spec(Dq,B); return np.array([s[1]-obs[1], s[2]-obs[2]])
for guess in [(433,600),(500,800),(430,1000)]:
    r=least_squares(res2,guess); print(r.x, spec(*r.x)[:3])
def res3(p):
    Dq,B=p; s=spec(Dq,B); return np.array([s[0]-obs[0], s[1]-obs[1]])
r=least_squares(res3,(433,600)); print('nu1,nu2', r.x, spec(*r.x)[:3])
def res4(p):
    Dq,B=p; s=spec(Dq,B); return np.array([s[0]-obs[0], s[2]-obs[2]])
r=least_squares(res4,(433,600)); print('nu1,nu3', r.x, spec(*r.x)[:3])
