python3 -c "
import numpy as np
from scipy.optimize import brentq,least_squares
D=1230
f=lambda B,s:7.5*B+15*D+s*0.5*np.sqrt(225*B*B+100*D*D-180*B*D)
print(brentq(lambda B:f(B,-1)-18500,300,1500),brentq(lambda B:f(B,1)-27900,300,1500))
r=least_squares(lambda p:[10*p[0]-12300,7.5*p[1]+15*p[0]-0.5*np.sqrt(225*p[1]**2+100*p[0]**2-180*p[1]*p[0])-18500,7.5*p[1]+15*p[0]+0.5*np.sqrt(225*p[1]**2+100*p[0]**2-180*p[1]*p[0])-27900],[1230,640]);print(r.x,r.fun)
"