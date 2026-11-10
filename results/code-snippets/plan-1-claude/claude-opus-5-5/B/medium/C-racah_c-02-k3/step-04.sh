
cd $TMPDIR && cat >> d3.py << 'EOF'
print("free",np.round(np.linalg.eigvalsh(build(0,600,2400))-np.linalg.eigvalsh(build(0,600,2400))[0])[:60])
EOF
python3 d3.py 2>&1 | tail -8
