def res2(x):
    L=levels(*x)
    return [L[1][0]-19180,L[2][0]-22130,10*x[1]+5*x[2]-23370]
s=least_squares(res2,[700,700,3200]);print(s.x,res2(s.x),levels(*s.x)[:6])
for st in ([1000,600,3500],[500,800,3000],[900,650,3300]):
    s=least_squares(res2,st);print(s.x,res2(s.x))
