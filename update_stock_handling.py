import os, textwrap, pathlib, json, base64

root = pathlib.Path(os.getcwd())

# Update README to reflect that stock is not validated
readme_path = root / "README.md"
content = readme_path.read_text(encoding='utf-8')
# Insert a note under "How to test the core flow"
insert_point = content.find('## ✅ How to test the core flow')
note = textwrap.dedent('''
## 📦 Business Rules – Stock Handling

- **Zero or negative stock does NOT block an order.** The online store is a *catalogue‑only* front‑end; the store decides later whether to fulfil, back‑order or cancel.
- The API does **not** check the original MARG CSV for available quantity – it simply records the order with the requested quantity and price.
- This matches the reality that the on‑hand inventory may differ from the exported data (e.g., expiries, manual adjustments).

''')
new_content = content[:insert_point] + note + content[insert_point:]
readme_path.write_text(new_content, encoding='utf-8')

# Update backend/crud.py to remove stock‑related comment and ensure no validation on stock
crud_path = root / "backend" / "app" / "crud.py"
crud_code = crud_path.read_text(encoding='utf-8')
# Replace the comment block about stock verification
crud_code = crud_code.replace(
    "# Verify stock internally (stock is NOT stored; we rely on the original CSV backup)\n    # For demo we just accept any qty >0.",
    "# No stock verification – the platform is a catalogue only.\n    # Orders are recorded regardless of current stock levels."
)
crud_path.write_text(crud_code, encoding='utf-8')

print('README and crud updated')
