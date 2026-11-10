export MPLCONFIGDIR=/tmp/mpl && cat > dbg.py << 'EOF'
exec(open('ts.py').read().split("csz=[")[0].replace("for k in ckeys: assert","#"))
for k in ckeys:
    Dm=Dmat(classes[k][0]); print(k, np.abs(Dm@Dm.T-np.eye(5)).max(), np.abs(Gs[k]@Hee3-Hee3@Gs[k]).max())
print(np.abs(Hee-Hee.T).max(), np.abs(Hee3-Hee3.T).max())
EOF
python3 dbg.py 2>&1 | grep -v matplotlib