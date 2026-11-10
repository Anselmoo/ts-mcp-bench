cat > dbg.py << 'EOF'
from ts import *
print("Lz eig set:", sorted(set(np.round(np.linalg.eigvalsh(Lz),6))))
print("L2 eig:", sorted(set(np.round(np.linalg.eigvals(L2).real,6))))
for c in order:
    print(c, np.round(np.trace(classes[c][1]),6))
print("commutator [Lx,Ly]-iLz:", np.abs(Lx@Ly-Ly@Lx-1j*Lz).max())
EOF
<B_VENV>/bin/python3 dbg.py