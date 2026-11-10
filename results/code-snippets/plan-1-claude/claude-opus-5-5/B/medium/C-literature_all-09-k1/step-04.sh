cd $TMPDIR && python3 - << 'EOF' 2>&1 | tail -5
exec(open('/dev/stdin').read()) if False else None
EOF
echo