python3 - << 'EOF'
import re
src=open('d5.py').read()
src=src.replace("F = forb(P)\nF = F/np.sqrt(np.einsum('k,ki->i', W, F**2))",
"F0 = forb(P)\nNRM = np.sqrt(np.einsum('k,ki->i', W, F0**2))\nF = F0/NRM")
src=src.replace("    Fp = forb(P@R)\n","    Fp = forb(P@R)/NRM\n")
src=src.split('print("Gram')[0]
src+='''
Us=[U5(R) for R in G]
print("orth", max(np.abs(U.T@U-np.eye(5)).max() for U in Us))
'''
open('d5.py','w').write(src)
EOF
python3 d5.py