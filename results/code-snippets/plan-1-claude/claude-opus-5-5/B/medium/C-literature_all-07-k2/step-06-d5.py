obs=np.array([19240,21890,23000])
def res(p):
    L=levels(*p); return np.array([L[0][0],L[1][0],L[2][0]])-obs
r=least_squares(res,[800,700,3200]); print(r.x, res(r.x)); print(levels(*r.x)[:4])
