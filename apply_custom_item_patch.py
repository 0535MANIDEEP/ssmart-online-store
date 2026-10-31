## Backend updates

# 1️⃣ Extend the SQLAlchemy model to store optional notes and allow custom items
# File: backend/app/models.py

# Add a new column `note` to OrderItem and make `product_id` nullable
# Also allow `price` to be nullable for custom items (price can be set later by staff)

# Locate the OrderItem definition and replace it with the updated version

import pathlib, re, textwrap, os

model_path = os.path.join(os.getcwd(), 'backend', 'app', 'models.py')
content = open(model_path, 'r', encoding='utf-8').read()

pattern = r"class OrderItem\(Base\):\n    __tablename__ = 'order_item'\n    id\s+= Column\(Integer, primary_key=True, index=True\)\n    order_id\s+= Column\(Integer, nullable=False\)\n    product_id\s+= Column\(Integer, nullable=False\)\n    qty\s+= Column\(Integer, nullable=False\)\n    price\s+= Column\(Float, nullable=False\)"

new_def = textwrap.dedent('''
class OrderItem(Base):
    __tablename__ = 'order_item'
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False)
    product_id = Column(Integer, nullable=True)  # may be NULL for custom items
    qty = Column(Integer, nullable=False)
    price = Column(Float, nullable=True)        # price can be NULL for custom items
    note = Column(String, nullable=True)        # free‑form note / customisation
''')

new_content = re.sub(pattern, new_def, content, flags=re.MULTILINE)
open(model_path, 'w', encoding='utf-8').write(new_content)

# 2️⃣ Extend Pydantic schemas to accept a note per order item and optional custom items
# File: backend/app/schemas.py

schema_path = os.path.join(os.getcwd(), 'backend', 'app', 'schemas.py')
schema_content = open(schema_path, 'r', encoding='utf-8').read()

# Add a new model for custom items
custom_item = textwrap.dedent('''
class CustomItem(BaseModel):
    name: str                     # free‑form product name
    qty: int = Field(..., gt=0)
    price: float | None = None    # optional price (staff can fill later)
    note: str | None = None       # optional note/customisation
''')

# Insert after CartItem definition
insert_pos = schema_content.find('class CartItem')
after_cart = schema_content[insert_pos:]
# find end of CartItem class
end_cart = after_cart.find('}') + 1
new_schema_content = (
    schema_content[:insert_pos] +
    after_cart[:end_cart] +
    '\n' + custom_item +
    after_cart[end_cart:]
)

# Update OrderCreate to allow a list of custom_items
order_create_pattern = r"class OrderCreate\(BaseModel\):\n    customer: str\n    phone: Optional\[str\] = None\n    address: Optional\[str\] = None\n    items: List\[CartItem\]"
new_order_create = textwrap.dedent('''
class OrderCreate(BaseModel):
    customer: str
    phone: Optional[str] = None
    address: Optional[str] = None
    items: List[CartItem]
    custom_items: List[CustomItem] | None = None
''')
new_schema_content = re.sub(order_create_pattern, new_order_create, new_schema_content, flags=re.MULTILINE)
open(schema_path, 'w', encoding='utf-8').write(new_schema_content)

# 3️⃣ Update CRUD to handle custom items during order creation
# File: backend/app/crud.py

crud_path = os.path.join(os.getcwd(), 'backend', 'app', 'crud.py')
crud_code = open(crud_path, 'r', encoding='utf-8').read()

# Extend create_order function signature to accept custom_items
new_create_order = textwrap.dedent('''
def create_order(db: Session, customer: str, phone: str, address: str, items: List[CartItem], custom_items: List[dict] | None = None):
    """Create an order from catalogue items *and* optional custom items.
    Custom items do not need a product_id; they are stored with a note.
    """
    total = 0.0
    # Process catalogue items
    for it in items:
        prod = get_product_by_code(db, it.code)
        if not prod:
            raise ValueError(f'Product code {it.code} not found')
        price = prod.mrp if prod.mrp else prod.rate or 0.0
        total += price * it.qty
    # Process custom items
    if custom_items:
        for ci in custom_items:
            # price may be None – treat as 0 for total calculation now
            price = ci.get('price') or 0.0
            total += price * ci.get('qty', 1)
    order = models.Order(customer=customer, phone=phone, address=address, total_price=total)
    db.add(order)
    db.flush()
    # Save catalogue items
    for it in items:
        prod = get_product_by_code(db, it.code)
        price = prod.mrp if prod.mrp else prod.rate or 0.0
        db_item = models.OrderItem(order_id=order.id, product_id=prod.id, qty=it.qty, price=price)
        db.add(db_item)
    # Save custom items
    if custom_items:
        for ci in custom_items:
            db_item = models.OrderItem(
                order_id=order.id,
                product_id=None,
                qty=ci.get('qty'),
                price=ci.get('price'),
                note=ci.get('note') or ci.get('name')  # store the free‑form name in note as fallback
            )
            db.add(db_item)
    db.commit()
    db.refresh(order)
    return order
''')

# Replace the old create_order definition
old_def_pattern = r"def create_order\(.*?\):\n(?:\s+.*\n)+"
new_crud_code = re.sub(old_def_pattern, new_create_order, crud_code, flags=re.DOTALL)
open(crud_path, 'w', encoding='utf-8').write(new_crud_code)

# 4️⃣ Update FastAPI orders router to accept the new payload field
# File: backend/app/routers/orders.py

orders_path = os.path.join(os.getcwd(), 'backend', 'app', 'routers', 'orders.py')
orders_code = open(orders_path, 'r', encoding='utf-8').read()

# Change the call to crud.create_order to pass payload.custom_items
new_route = textwrap.dedent('''
@router.post('/', status_code=201)
def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    try:
        order = crud.create_order(
            db,
            customer=payload.customer,
            phone=payload.phone,
            address=payload.address,
            items=payload.items,
            custom_items=getattr(payload, 'custom_items', None)
        )
        return {"order_id": order.id, "total": order.total_price}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
''')
# Replace the whole function definition
new_orders_code = re.sub(r"@router\.post\('\/',.*?\)\ndef create_order\(.*?\):\n(?:\s+.*\n)+", new_route, orders_code, flags=re.DOTALL)
open(orders_path, 'w', encoding='utf-8').write(new_orders_code)

# 5️⃣ Front‑end – allow adding a custom item and per‑item notes
# File: frontend/src/App.jsx

app_path = os.path.join(os.getcwd(), 'frontend', 'src', 'App.jsx')
app_code = open(app_path, 'r', encoding='utf-8').read()

# Insert a new UI section for a custom item form above the product grid
custom_section = textwrap.dedent('''
  // ---------- Custom item entry ----------
  const [customName, setCustomName] = useState('');
  const [customQty, setCustomQty] = useState(1);
  const [customPrice, setCustomPrice] = useState('');
  const [customNote, setCustomNote] = useState('');
  const addCustomToCart = () => {
    if (!customName.trim()) { alert('Enter a name for the custom item'); return; }
    const price = parseFloat(customPrice) || 0;
    setCustomItems(prev => [...prev, { name: customName, qty: customQty, price, note: customNote }]);
    // reset fields
    setCustomName(''); setCustomQty(1); setCustomPrice(''); setCustomNote('');
  };
''' )

# We'll add a state hook for custom items at top of component
app_code = app_code.replace('const [cart, setCart] = useState([]);', 'const [cart, setCart] = useState([]);
  const [customItems, setCustomItems] = useState([]);')

# Insert the custom_section after the existing state declarations (right after useEffect block start)
app_code = app_code.replace('useEffect(() => {', 'useEffect(() => {')
# Find the closing brace of useEffect (first occurrence of '}, []);')
idx = app_code.find('}, []);')
if idx != -1:
    insertion_point = idx + len('}, []);')
    app_code = app_code[:insertion_point] + '\n' + custom_section + app_code[insertion_point:]

# Add a UI block for the custom item form just before the product grid (inside return)
custom_form = textwrap.dedent('''
        <section className="my-4 p-4 bg-white rounded shadow">
          <h2 className="text-lg font-semibold mb-2">Add a custom item (not in catalogue)</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
            <input className="border p-1" placeholder="Item name" value={customName} onChange={e=>setCustomName(e.target.value)} />
            <input type="number" min="1" className="border p-1" placeholder="Qty" value={customQty} onChange={e=>setCustomQty(parseInt(e.target.value)||1)} />
            <input className="border p-1" placeholder="Price (₹) – optional" value={customPrice} onChange={e=>setCustomPrice(e.target.value)} />
            <input className="border p-1" placeholder="Note / customisation" value={customNote} onChange={e=>setCustomNote(e.target.value)} />
            <button className="col-span-4 bg-indigo-600 hover:bg-indigo-700 text-white py-1 rounded" onClick={addCustomToCart}>Add Custom Item</button>
          </div>
        </section>
''')
# Insert before the product grid (`<main className="p-4 grid ...`)
app_code = app_code.replace('<main className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">', custom_form + '\n<main className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">')

# Update placeOrder to also send customItems payload
place_order_patch = textwrap.dedent('''
  const placeOrder = () => {
    if (cart.length===0 && customItems.length===0) { alert('Cart empty'); return; }
    const payload = {
      customer: 'Demo Customer',
      phone: '',
      address: '',
      items: cart,
      custom_items: customItems
    };
    axios.post('http://localhost:8000/orders/', payload)
      .then(r => {
        alert(`Order placed! ID=${r.data.order_id}, total ₹${r.data.total}`);
        setCart([]);
        setCustomItems([]);
      })
      .catch(err => {
        console.error(err);
        alert('Order failed: ' + err.response?.data?.detail);
      });
  };
''')
app_code = re.sub(r'const placeOrder = \(\) => \{[^}]*\};', place_order_patch, app_code, flags=re.DOTALL)

# Save the updated App.jsx
open(app_path, 'w', encoding='utf-8').write(app_code)

# 6️⃣ Add a simple frontend test (optional) – not required for now.

print('All updates applied')
