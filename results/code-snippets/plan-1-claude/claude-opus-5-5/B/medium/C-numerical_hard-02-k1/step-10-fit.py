from scipy.optimize import least_squares
def res(p):
    g,q=lev(p[0],p[1],4.3*p[1]); return np.array([x for x,n in g[1:4]])-obs
for s in best[:3]:
    r=least_squares(res,[s[1],s[2]]); print(r.x, res(r.x), lev(r.x[0],r.x[1],4.3*r.x[1])[0][:4], lev(r.x[0],r.x[1],4.3*r.x[1])[1])
