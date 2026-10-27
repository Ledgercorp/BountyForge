```python
import json
import PyPDF2

def pdf_to_json(filename):
    with open(filename, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = reader.extract_text()
        lines = text.split('\n')
        data = {}
        current_key = None
        for line in lines:
            if line.startswith('Field:'):
                current_key = line[len('Field:'):].strip()
            elif current_key:
                data[current_key] = line.strip()
                current_key = None
        return json.dumps(data, indent=2)

# Example usage:
# Extracted JSON will be a string representation of the data.
```