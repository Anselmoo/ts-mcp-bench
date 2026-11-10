cd /tmp && python3 - << 'EOF'
exec(open('/dev/null').read())
EOF
cat > /dev/null << 'EOF'
EOF
python3 -c "print('ok')"; ls /tmp/tsbench-run-1cj522g6 2>/dev/null | head -2