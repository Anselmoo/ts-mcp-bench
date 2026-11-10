python3 - << 'EOF'
import re
src=open('ts.py').read()
src=src.replace("""    x=9*CB/(35+45*CB)
    F2=49*B/(1-5*x); F4=x*F2""","""    C=CB*B
    F4=441*C/35; F2=(441*B+5*F4)/9""")
open('ts.py','w').write(src)
import ts, numpy as np
e=ts.levels(0,1000)
print(np.round(e,3))
EOF