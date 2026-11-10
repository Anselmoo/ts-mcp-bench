python3 -c "
from scan import triplet_levels
for x in [2.0,2.5,3.0,3.83]:
    lev=triplet_levels(x)
    print(x,[(round(a-lev[0][0],2),m) for a,m in lev[:9]])
" 2>/dev/null