import re
src=open('fit.py').read()
src=src.replace("""    T=[x for x,m in lv if m==3 and x>1e-6]
    return T""","""    T=[x for x,m in lv if x>1e-6]
    return T""")
src=src.replace("print(levels(1000,500,2250))","")
src=src.replace("print(np.round(spectrum(1,0,0),4))\nprint(np.round(spectrum(0,1,0),4))","")
open('fit2.py','w').write(src)
