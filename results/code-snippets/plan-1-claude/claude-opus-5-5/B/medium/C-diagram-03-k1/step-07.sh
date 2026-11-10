cat >> ts.py <<'EOF'
print(classify(1e-3)[:8])
EOF
MPLCONFIGDIR=<SANDBOX_TMP> python3 ts.py | tail -1; sha256sum diagram.png; realpath diagram.png