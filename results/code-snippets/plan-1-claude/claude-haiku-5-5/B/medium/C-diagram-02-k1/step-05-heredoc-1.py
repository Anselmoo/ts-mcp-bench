import re
src = open('ts_calc.py').read()
src = src.replace("n = sum(chi[g]*tab[classes[g]] for g in range(24))/24",
                  "n = sum(chi[g]*tab[classes[g]] for g in range(24))/24/mult")
open('ts_calc.py','w').write(src)
