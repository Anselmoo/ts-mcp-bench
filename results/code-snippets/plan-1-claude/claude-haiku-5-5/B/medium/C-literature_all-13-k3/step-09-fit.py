
def nu(p):
    vals,mult=resid(p)
    # expect: [T1F(3), T2(3), A2(1), T1P(3)]
    assert list(mult)==[3,3,1,3], mult
    g=vals[0]
    return np.array([vals[1]-g, vals[2]-g, vals[3]-g])
def res(p):
    return nu(p)-obs
sol=least_squares(res,[700,700,3500],x_scale=[100,100,500])
print(sol.x, res(sol.x), nu(sol.x))
Dq,B,C=sol.x
print("Dq",Dq,"B",B,"C",C,"C/B",C/B)
# doublet check: not in quartet model
