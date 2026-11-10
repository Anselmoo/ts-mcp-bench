print(c(2,0,0),c(4,0,0))
f=lambda D:gs(D,2)-gs(D,0)
for D in (1000,1500,2000,2500,3000):print(D,f(D))
print(brentq(f,1000,3500))
