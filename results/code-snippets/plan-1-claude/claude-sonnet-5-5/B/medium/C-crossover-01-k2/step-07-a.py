for D in (0,200,400,600,800):print(D,f(D))
print(brentq(f,0,1000,xtol=0.01))
