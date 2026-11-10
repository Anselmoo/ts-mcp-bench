import re
s=open('d4.py').read()
s=s.replace("from scipy.special import sph_harm\n","from scipy.special import sph_harm_y\n")
s=s.replace("    return sph_harm(q, k, ph, np.arccos(ct))","    return sph_harm_y(k, q, np.arccos(ct), ph)")
open('d4.py','w').write(s)
