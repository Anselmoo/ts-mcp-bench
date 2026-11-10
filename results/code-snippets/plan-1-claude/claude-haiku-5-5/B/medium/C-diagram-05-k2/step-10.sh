cat > dbg2.py << 'EOF'
from ts import *
print("trace exp(-i pi Lz) direct:", np.trace(expm(-1j*pi*Lz)))
print("sum e^{-i pi M}:", np.sum(np.exp(-1j*pi*np.diag(Lz))))
print("diag Lz",np.unique(np.diag(Lz)))
print("is Lz diagonal?", np.abs(Lz-np.diag(np.diag(Lz))).max())
print("trace of exp(-i pi/2 Lz):", np.trace(expm(-1j*pi/2*Lz)))
print("eigs of expm rot about z by pi:", np.round(np.linalg.eigvals(classes['C2'][1])[:5],3))
EOF
<B_VENV>/bin/python3 dbg2.py 2>&1 | tail -6