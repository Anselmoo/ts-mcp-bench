cat << 'EOF' > /dev/null
EOF
cd $HOME 2>/dev/null; cat << 'EOF' | python3 - 
exec(open('/dev/stdin').read()) if False else None
EOF
echo