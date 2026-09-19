from pathlib import Path
from html import escape
P=Path(__file__).resolve().parent
nodes=[('customer','Заказчик',20,20,['PK customer_id','full_name, phone, email']),('instrument','Инструмент',330,20,['PK instrument_id','UQ inventory_no','FK customer_id, type_id','name, maker, serial_no']),('instrument_type','Тип инструмента',640,20,['PK type_id; UQ name','description']),('payment','Оплата',20,230,['PK payment_id; FK order_id','paid_on, amount_kopecks','method; UQ receipt_no']),('restoration_order','Заказ',330,230,['PK order_id; FK instrument_id','accepted_on, due_on','status, complaint']),('inspection','Осмотр',640,230,['PK inspection_id','FK order_id, employee_id','inspected_on, conclusion']),('service','Вид работы',20,440,['PK service_id; UQ name','description, base_price_kopecks']),('order_work','Работа по заказу',330,440,['PK (order_id, line_no)','FK order_id','FK service_id, employee_id','agreed_price_kopecks, status']),('employee','Реставратор',640,440,['PK employee_id','UQ work_email','full_name, specialization'])]
s=['<svg xmlns="http://www.w3.org/2000/svg" width="920" height="615" viewBox="0 0 920 615">','<rect width="920" height="615" fill="white"/>','<g font-family="Arial, sans-serif" fill="black">']
def edge(x1,y1,x2,y2,left,right):
 s.append(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="black" fill="none" stroke-width="1.7"/>')
 if y1==y2:
  s.append(f'<text x="{x1+5}" y="{y1-9}" font-size="16">{left}</text><text x="{x2-5}" y="{y2+20}" text-anchor="end" font-size="16">{right}</text>')
 else:
  s.append(f'<text x="{x1+8}" y="{y1+18}" font-size="16">{left}</text><text x="{x2+8}" y="{y2-9}" font-size="16">{right}</text>')
edge(280,80,330,80,'1','0..N');edge(590,80,640,80,'0..N','1')
edge(460,150,460,230,'1','0..N')
edge(280,290,330,290,'0..N','1');edge(590,290,640,290,'1','0..N')
edge(460,360,460,440,'1','0..N')
edge(280,500,330,500,'1','0..N');edge(590,500,640,500,'0..N','1')
edge(770,360,770,440,'0..N','1')
for ident,title,x,y,attrs in nodes:
 s.append(f'<rect x="{x}" y="{y}" width="260" height="130" rx="3" fill="white" stroke="black" stroke-width="1.5"/>')
 s.append(f'<text x="{x+130}" y="{y+25}" text-anchor="middle" font-size="19" font-weight="bold">{title}</text>')
 s.append(f'<path d="M{x} {y+38} H{x+260}" stroke="black"/>')
 for j,a in enumerate(attrs):s.append(f'<text x="{x+10}" y="{y+55+j*20}" font-size="16">{escape(a)}</text>')
s.append('<text x="460" y="603" text-anchor="middle" font-size="14">PK — первичный ключ; FK — внешний ключ; UQ — альтернативный ключ</text></g></svg>')
(P/'er.svg').write_text('\n'.join(s))
