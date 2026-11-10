cat > t4.py << 'EOF'
from ts import *
def levels(F):
    q,_=Hmat(F,0.0,Sz2=3); H1,_=Hmat(F,0.0,Sz2=1)
    eq=np.sort(np.linalg.eigvalsh(q)); e1=np.sort(np.linalg.eigvalsh(H1))
    # doublets: remove quartet eigenvalues from Sz=1/2 spectrum
    rem=list(e1)
    for x in eq:
        j=min(range(len(rem)),key=lambda i:abs(rem[i]-x)); rem.pop(j)
    return eq, np.array(rem)
for F in [{0:0,2:1,4:0},{0:0,2:0,4:1}]:
    eq,ed=levels(F)
    print("quartets", np.round(eq-eq.min(),4)[[0,-1]], "distinct:", sorted(set(np.round(eq-eq.min(),4))))
    print("doublets distinct:", sorted(set(np.round(ed-eq.min(),4))))
EOF
python3 t4.py