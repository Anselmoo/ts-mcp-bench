cat << 'EOF' | python3 - 2>/dev/null
exec(open('/dev/stdin').read()) if False else None
EOF
echo skip