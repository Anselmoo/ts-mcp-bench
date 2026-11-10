cat >> fit2.py << 'EOF'
print(levels(2228.89494329,763.83999664,3000))
EOF
python3 fit2.py 2>&1 | tail -1