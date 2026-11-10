cat << 'EOF' > dbg.py
exec(open('d5.py').read().split('for Dq in')[0])
print("ak2 diag", ak[2][0,0,0,0], ak[2][0,0,1,1], ak[2][0,1,0,1], "ak4",ak[4][0,0,0,0], ak[4][0,0,1,1])
print("H2 eig range", np.linalg.eigvalsh(H2)[[0,-1]])
print("Vso max", Vso.max(), len(terms))
print("hd eig", np.linalg.eigvalsh(hd_op(1.0))[[0,-1]])
EOF
python3 dbg.py