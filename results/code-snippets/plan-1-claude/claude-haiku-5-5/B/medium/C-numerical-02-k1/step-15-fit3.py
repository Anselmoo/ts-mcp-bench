
print("--- scan F4/F2 ratio")
for r_ in [0.0,0.3,0.5,0.625,0.7,0.8]:
    def res2(p):
        Dq,F2=p
        return res([Dq,F2,r_*F2])
    bb=None
    for Dq0 in [700,1000]:
        for F20 in [800,1200]:
            rr=least_squares(res2,[Dq0,F20],xtol=1e-14,ftol=1e-14,gtol=1e-14)
            if bb is None or rr.cost<bb.cost: bb=rr
    Dq,F2=bb.x
    print(r_, np.round(bb.x,1), np.round(bb.fun,1), "B=",round((9*F2-5*r_*F2)/441,1))
