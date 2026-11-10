cat > t6.py << 'EOF'
from ts import *
def levels(F):
    q,_=Hmat(F,0.0,Sz2=3); H1,_=Hmat(F,0.0,Sz2=1)
    eq=np.sort(np.linalg.eigvalsh(q)); e1=np.sort(np.linalg.eigvalsh(H1))
    rem=list(e1)
    for x in eq:
        j=min(range(len(rem)),key=lambda i:abs(rem[i]-x)); rem.pop(j)
    return eq, np.array(rem)
from collections import Counter
for F in [{0:0,2:1,4:0},{0:0,2:0,4:1}]:
    eq,ed=levels(F)
    print("quartet:",Counter(np.round(eq-eq[0],5)))
    print("doublet:",Counter(np.round(ed-eq[0],5)))
EOF
python3 t6.py