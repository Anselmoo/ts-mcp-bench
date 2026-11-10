sed -i 's/e>26000/e>27000/' solve.py && sed -i 's/^t=time.time()/if __name__=="__main__": pass\nt=time.time()/' fit.py && python3 - << 'EOF'
import re
src=open('fit.py').read()
src=src.replace("t=time.time()\nH=build_H(2660,700,3000)\nprint('time',time.time()-t)\nL=levels(H)\ng=L[0][0]\nfor e,d in L: print(round(e-g,2),d)\n","")
open('fit.py','w').write(src)
EOF
python3 solve.py