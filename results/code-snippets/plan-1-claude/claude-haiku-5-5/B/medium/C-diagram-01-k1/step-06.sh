cat > dbg2.py << 'EOF'
exec(open('ts.py').read().split("csz=[")[0].replace("for k in ckeys: assert","#"))
u=np.kron(Dmat(classes['C3'][0]),np.eye(2))
K=sla.logm(u); print(np.abs(sla.expm(K)-u).max())
print(np.abs(u.conj().T@u-np.eye(10)).max())
EOF
python3 dbg2.py 2>&1 | tail -2