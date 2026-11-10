cd $TMPDIR; cat >> d7.py << 'EOF'
EOF
sed -i 's/^Dq=brentq.*$/import sys\nfor D in [0,500,1000,1500,2000,2500,3000,5000]: print(D,lev(D))\nw,v=np.linalg.eigh(H2);print(np.round(w[:12]-w[0]));print(np.round(np.einsum("ij,ik,kj->j",v,S2,v)[:12],3))/' d7.py; python3 d7.py