from f import *
def r3(p):
    return res((p[0],3800,p[1]))[:3]
for g in [(900,900),(800,1000),(1000,800)]:
    s=least_squares(r3,g,diff_step=1e-3,x_scale=[100,100]);print(s.x,s.fun)
