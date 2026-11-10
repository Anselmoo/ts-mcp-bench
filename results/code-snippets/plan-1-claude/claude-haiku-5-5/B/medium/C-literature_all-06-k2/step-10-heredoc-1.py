import re
src=open('fit.py').read()
src=src.replace("t=time.time()\nH=build_H(2660,700,3000)\nprint('time',time.time()-t)\nL=levels(H)\ng=L[0][0]\nfor e,d in L: print(round(e-g,2),d)\n","")
open('fit.py','w').write(src)
