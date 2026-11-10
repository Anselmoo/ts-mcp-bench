for drop in obs:
    ks=[k for k in obs if k!=drop]
    f=lambda x:[dict((n,e) for e,n in names(*x))[k]-obs[k] for k in ks]
    r=least_squares(f,[890,915,3800]); print(drop,r.x,f(r.x))
