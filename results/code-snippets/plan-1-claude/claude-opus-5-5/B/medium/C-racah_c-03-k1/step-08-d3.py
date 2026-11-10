def low_doublet(C):
    u=lev(1917,824,C); return u[1]
for C in np.arange(3000,4200,100): print(C,[(round(a,1),b) for a,b in lev(1917,824,C)[1:4]])
f=lambda C: lev(1917,824,C)[1][0]-17050
Cs=brentq(f,3000,4500); print(Cs, lev(1917,824,Cs)[:5], Cs/824)
