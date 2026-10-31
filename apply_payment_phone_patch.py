# Update backend models to store payment phone number (optional)
# File: backend/app/models.py

import pathlib, re, os

model_path = os.path.join(os.getcwd(), 'backend', 'app', 'models.py')
content = open(model_path, 'r', encoding='utf-8').read()

# Insert a new column `payment_phone` into the Order class
pattern = r"class Order\(Base\):\n    __tablename__ = 'order'\n    id\s+= Column\(Integer, primary_key=True, index=True\)\n    created_at\s+= Column\(DateTime, default=datetime\.datetime\.utcnow\)\n    customer\s+= Column\(String, nullable=False\)\n    phone\s+= Column\(String, nullable=True\)\n    address\s+= Column\(String, nullable=True\)\n    total_price\s+= Column\(Float, nullable=False\)\n    paid\s+= Column\(Boolean, default=False\)"

replacement = """class Order(Base):
    __tablename__ = 'order'
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    customer = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    total_price = Column(Float, nullable=False)
    paid = Column(Boolean, default=False)
    payment_phone = Column(String, nullable=False, default='9849530828')  # store's payment contact
"""

new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
open(model_path, 'w', encoding='utf-8').write(new_content)

# Update CRUD to set payment_phone when creating an order
crud_path = os.path.join(os.getcwd(), 'backend', 'app', 'crud.py')
crud_code = open(crud_path, 'r', encoding='utf-8').read()

# Find the Order creation line and add payment_phone argument
order_create_pattern = r"order = models\.Order\(customer=customer, phone=phone, address=address, total_price=total\)"
new_order_line = "order = models.Order(customer=customer, phone=phone, address=address, total_price=total, payment_phone='9849530828')"
crud_code = re.sub(order_create_pattern, new_order_line, crud_code)
open(crud_path, 'w', encoding='utf-8').write(crud_code)

# Update schemas to expose payment_phone in order response (optional)
schema_path = os.path.join(os.getcwd(), 'backend', 'app', 'schemas.py')
schema_code = open(schema_path, 'r', encoding='utf-8').read()

# Add a new response model for OrderOut
order_out_model = """
class OrderOut(BaseModel):
    order_id: int
    total: float
    payment_phone: str
    message: str = 'Please pay the above amount to the store via the phone number provided.'
    class Config:
        orm_mode = True
"""
# Insert after OrderCreate definition
insert_point = schema_code.find('class OrderCreate')
if insert_point != -1:
    # Find end of OrderCreate class (first blank line after it)
    end_idx = schema_code.find('\n\n', insert_point)
    schema_code = schema_code[:end_idx] + '\n' + order_out_model + schema_code[end_idx:]
open(schema_path, 'w', encoding='utf-8').write(schema_code)

# Update orders router to return OrderOut instead of dict
orders_path = os.path.join(os.getcwd(), 'backend', 'app', 'routers', 'orders.py')
orders_code = open(orders_path, 'r', encoding='utf-8').read()

# Replace the return dict with OrderOut model
new_route = """
@router.post('/', response_model=schemas.OrderOut, status_code=201)
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
        return schemas.OrderOut(order_id=order.id, total=order.total_price, payment_phone=order.payment_phone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
"""
# Replace the whole function definition
orders_code = re.sub(r"@router\.post\('\/',.*?\)\ndef create_order\(.*?\):\n(?:\s+.*\n)+", new_route, orders_code, flags=re.DOTALL)
open(orders_path, 'w', encoding='utf-8').write(orders_code)

# Front‑end changes – show payment instructions after order success
app_path = os.path.join(os.getcwd(), 'frontend', 'src', 'App.jsx')
app_code = open(app_path, 'r', encoding='utf-8').read()

# Replace the alert after order placement with a richer message
new_place_order = '''
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
        const msg = `Order placed! ID=${r.data.order_id}, total ₹${r.data.total}.\nPlease pay ₹${r.data.total} to ${r.data.payment_phone} (store phone).`;
        alert(msg);
        setCart([]);
        setCustomItems([]);
      })
      .catch(err => {
        console.error(err);
        alert('Order failed: ' + err.response?.data?.detail);
      });
  };
'''
app_code = re.sub(r'const placeOrder = \(\) => \{[^}]*\};', new_place_order, app_code, flags=re.DOTALL)
open(app_path, 'w', encoding='utf-8').write(app_code)

print('All patches applied')
