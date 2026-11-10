f=lambda C: levels(C)[4]-12710
Cs=brentq(f,1500,4000,xtol=0.01); print(Cs, Cs/B); print(np.round(levels(Cs)[:50]))
