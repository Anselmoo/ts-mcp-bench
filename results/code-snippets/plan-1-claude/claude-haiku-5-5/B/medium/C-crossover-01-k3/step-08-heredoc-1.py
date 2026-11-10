import re
src=open('d4.py').read()
src=src.split("for Dq in [0,500")[0]+src.split("print(Dq, lowest_by_spin(Dq))\n")[1] if False else src
open('d4b.py','w').write(src)
