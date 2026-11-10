cat << 'EOF' | python3
exec(open('/dev/stdin').read()) if False else None
EOF
echo