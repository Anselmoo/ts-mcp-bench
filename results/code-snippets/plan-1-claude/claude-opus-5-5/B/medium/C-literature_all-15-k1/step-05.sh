
cd <SANDBOX_TMP>; cat > t.py << 'EOF'
exec(open('d7.py').read().split("print(names")[0])
for e,n in names(0,1000,4000)[:]: pass
o=levels(0,1000,4000)
for e,m,l in o: print(round(e-o[0][0]),m,l)
EOF
python3 t.py | head -30
