
cat << 'EOF' > dbg.py
import numpy as np
exec(open('fit.py').read().split('if __name__')[0])
# Check orthonormality of orbitals and rotational invariance of Coulomb tensor
G=np.einsum('ip,jp,p->ij',orbs,orbs,W); print(np.round(G,6))
print("A2 sym check", np.abs(A2-A2.transpose(2,3,0,1)).max())
print("Ocf eig", np.round(np.linalg.eigvalsh(Ocf)[:3],3))
print("O2 eig", np.round(np.linalg.eigvalsh(O2)[:5],3), np.round(np.linalg.eigvalsh(O2)[-5:],3))
print("O4 eig", np.round(np.linalg.eigvalsh(O4)[:5],3), np.round(np.linalg.eigvalsh(O4)[-5:],3))
EOF
python3 dbg.py 2>&1 | tail -20
