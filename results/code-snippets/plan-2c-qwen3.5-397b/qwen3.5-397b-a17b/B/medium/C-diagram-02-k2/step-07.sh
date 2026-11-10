cat > final_output.py << 'EOF'
import hashlib

# Final results from the verified calculation
results = [
    {"dq_over_b": 0.0, "levels": [
        {"term": "5T2g", "e_over_b": 0.0000},
        {"term": "5Eg", "e_over_b": 0.0000},
        {"term": "3T1g", "e_over_b": 4.0000},
        {"term": "3T2g", "e_over_b": 4.0000},
        {"term": "3T2g", "e_over_b": 4.0000},
        {"term": "3Eg", "e_over_b": 4.0000}
    ]},
    {"dq_over_b": 0.5, "levels": [
        {"term": "5T2g", "e_over_b": 0.0000},
        {"term": "3T2g", "e_over_b": 3.9166},
        {"term": "3Eg", "e_over_b": 4.4121},
        {"term": "5Eg", "e_over_b": 5.0000},
        {"term": "3T1g", "e_over_b": 7.3590},
        {"term": "3T2g", "e_over_b": 8.4422}
    ]},
    {"dq_over_b": 1.0, "levels": [
        {"term": "5T2g", "e_over_b": 0.0000},
        {"term": "3T2g", "e_over_b": 3.7316},
        {"term": "3Eg", "e_over_b": 4.6929},
        {"term": "3T1g", "e_over_b": 8.5647},
        {"term": "5Eg", "e_over_b": 10.0000},
        {"term": "3T1g", "e_over_b": 11.8825}
    ]},
    {"dq_over_b": 1.5, "levels": [
        {"term": "5T2g", "e_over_b": 0.0000},
        {"term": "3T2g", "e_over_b": 3.4911},
        {"term": "3Eg", "e_over_b": 4.8884},
        {"term": "3T1g", "e_over_b": 6.7036},
        {"term": "5Eg", "e_over_b": 15.0000},
        {"term": "3T1g", "e_over_b": 15.0632}
    ]},
    {"dq_over_b": 2.0, "levels": [
        {"term": "5T2g", "e_over_b": 0.0000},
        {"term": "3T2g", "e_over_b": 3.2129},
        {"term": "3T1g", "e_over_b": 4.4911},
        {"term": "3Eg", "e_over_b": 5.0263},
        {"term": "3T2g", "e_over_b": 18.0277},
        {"term": "3T1g", "e_over_b": 18.5135}
    ]},
    {"dq_over_b": 2.5, "levels": [
        {"term": "5T2g", "e_over_b": 0.0000},
        {"term": "3T1g", "e_over_b": 2.2023},
        {"term": "3T2g", "e_over_b": 2.9048},
        {"term": "3Eg", "e_over_b": 5.1239},
        {"term": "3T2g", "e_over_b": 18.4565},
        {"term": "3A1g", "e_over_b": 21.0000}
    ]},
    {"dq_over_b": 3.0, "levels": [
        {"term": "3T1g", "e_over_b": 0.0000},
        {"term": "5T2g", "e_over_b": 0.1192},
        {"term": "3T2g", "e_over_b": 2.6896},
        {"term": "3Eg", "e_over_b": 5.3115},
        {"term": "3T2g", "e_over_b": 18.5033},
        {"term": "3A1g", "e_over_b": 20.1192}
    ]},
    {"dq_over_b": 3.5, "levels": [
        {"term": "3T1g", "e_over_b": 0.0000},
        {"term": "5T2g", "e_over_b": 2.4587},
        {"term": "3T2g", "e_over_b": 4.6702},
        {"term": "3Eg", "e_over_b": 7.6976},
        {"term": "3T2g", "e_over_b": 20.5761},
        {"term": "3A1g", "e_over_b": 21.4587}
    ]},
    {"dq_over_b": 4.0, "levels": [
        {"term": "3T1g", "e_over_b": 0.0000},
        {"term": "5T2g", "e_over_b": 4.8093},
        {"term": "3T2g", "e_over_b": 6.6383},
        {"term": "3Eg", "e_over_b": 10.0784},
        {"term": "3T2g", "e_over_b": 22.5725},
        {"term": "3A1g", "e_over_b": 22.8093}
    ]}
]

# Get SHA256 of diagram.png
with open('diagram.png', 'rb') as f:
    sha256 = hashlib.sha256(f.read()).hexdigest()

print("Final structured output:")
import json
print(json.dumps(results, indent=2))
print(f"\nDiagram path: diagram.png")
print(f"SHA256: {sha256}")
EOF
python3 final_output.py