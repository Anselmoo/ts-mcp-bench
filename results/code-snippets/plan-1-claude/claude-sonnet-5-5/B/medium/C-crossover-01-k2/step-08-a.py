for D in (0,1000,2000,3000):print(D,f(D))
print(brentq(f,500,4000,xtol=0.01))
