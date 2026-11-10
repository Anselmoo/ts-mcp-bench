
cd ~ 2>/dev/null; cat > /dev/null; python3 - << 'EOF' 2>&1 | tail -5
exec(open('/dev/stdin').read()) if False else None
EOF
echo skip