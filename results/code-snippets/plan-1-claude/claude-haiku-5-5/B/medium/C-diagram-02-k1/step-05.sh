cd . && sed -i 's/for name, tab in irr.items():\n//' ts_calc.py && python3 - << 'EOF' 2>&1 | grep -vi matplotlib
import re
src = open('ts_calc.py').read()
src = src.replace("n = sum(chi[g]*tab[classes[g]] for g in range(24))/24",
                  "n = sum(chi[g]*tab[classes[g]] for g in range(24))/24/mult")
open('ts_calc.py','w').write(src)
EOF
python3 ts_calc.py 2>&1 | grep -vi matplotlib | tail -12