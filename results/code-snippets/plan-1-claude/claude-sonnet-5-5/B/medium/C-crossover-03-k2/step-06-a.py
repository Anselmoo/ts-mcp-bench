for D in (500,800,900,1000,1100,1200,1300): print(D,gap(D))
print(brentq(gap,1000,1500,xtol=0.01))
