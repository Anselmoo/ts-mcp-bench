python3 -c "
import ts
for dq in [0.0]:
    for E,l in ts.levels_for(dq): print(l, round(E,4))
" 2>/dev/null | head -60