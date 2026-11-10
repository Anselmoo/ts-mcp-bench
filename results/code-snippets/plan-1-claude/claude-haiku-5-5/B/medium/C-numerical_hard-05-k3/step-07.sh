cat << 'EOF' > run.py
import d6,numpy as np
def levels(x):
    w=d6.spectrum_singlet(x,1.0,4.5)
    w=w-w[0]
    # group
    groups=[]
    for e in w:
        if groups and abs(e-groups[-1][0])<1e-5: groups[-1][1]+=1
        else: groups.append([e,1])
    return groups
for x in [1.0,2.0,2.5,3.0]:
    g=levels(x)
    print(x,[(round(e,3),d) for e,d in g[:8]])
EOF
python3 run.py