from g import *
def three(p):
    e=lev(*p); u=[]
    for x in e[1:]:
        if not u or abs(x-u[-1])>1: u.append(x)
    return u[:3]
t=np.array([19720,23260,24980])
r=least_squares(lambda p:np.array(three(p))-t,[800,800,3000],x_scale=[100,100,300],diff_step=1e-4)
print(r.x,three(r.x))
