import json

filename = './data/reviews_devset.json'  # replace with your actual file path

with open(filename, 'r', encoding='utf-8') as f:
    data = [json.loads(line) for line in f]

print("Keys of the first JSON object:")
print(data[0].keys())

# Check if 'overall' is a number between 0 and 5.0 in all records
invalid_entries = []
for i, item in enumerate(data):
    overall = item.get('overall')
    if not isinstance(overall, (int, float)) or not (0 <= overall <= 5.0):
        invalid_entries.append((i, overall))

if invalid_entries:
    print("\nInvalid 'overall' entries found:")
    for idx, val in invalid_entries:
        print(f"Line {idx + 1}: overall = {val}")
else:
    print("\nAll 'overall' values are valid numbers between 0 and 5.0.")
