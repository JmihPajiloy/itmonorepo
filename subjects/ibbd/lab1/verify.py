"""Build a fresh demonstration database and verify meaningful invariants."""
from pathlib import Path
import sqlite3, json, csv
ROOT = Path(__file__).resolve().parent
con = sqlite3.connect(':memory:')
con.execute('PRAGMA foreign_keys=ON')
for name in ('01_schema.sql', '02_views.sql', '03_demo.sql'):
    con.executescript((ROOT/'sql'/name).read_text())
results=[]
def check(name, condition):
    assert condition, name
    results.append({'test':name,'result':'PASS'})
def reject(name, sql):
    con.execute('SAVEPOINT probe')
    try:
        con.execute(sql)
    except sqlite3.IntegrityError:
        results.append({'test':name,'result':'PASS'})
    else:
        raise AssertionError(name)
    finally:
        con.execute('ROLLBACK TO probe')
        con.execute('RELEASE probe')
check('9 tables, including 8 non-associative entities',len(con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())==9)
check('Every table has at least 3 attributes',all(len(con.execute('PRAGMA table_info('+r[0]+')').fetchall())>=3 for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")))
check('Foreign key integrity',not con.execute('PRAGMA foreign_key_check').fetchall())
check('Two works and two payments do not multiply totals',con.execute('SELECT agreed_kopecks,paid_kopecks,balance_kopecks FROM v_reception_balances WHERE order_id=1').fetchone()==(750000,300000,450000))
check('Unpaid order remains visible',con.execute('SELECT paid_kopecks,balance_kopecks FROM v_reception_balances WHERE order_id=2').fetchone()==(0,300000))
check('Task queue contains only 3 unfinished works',con.execute('SELECT count(*) FROM v_restorer_tasks').fetchone()[0]==3)
check('All 3 inspections are available',con.execute('SELECT count(*) FROM v_restorer_inspections').fetchone()[0]==3)
reject('Dangling foreign key rejected',"INSERT INTO instrument VALUES(9,999,1,'X','Test',NULL,NULL)")
reject('Duplicate inventory number rejected',"INSERT INTO instrument VALUES(9,1,1,'INS-001','Test',NULL,NULL)")
reject('Second active order rejected',"INSERT INTO restoration_order VALUES(9,1,'2026-09-12','2026-09-20','accepted','Test')")
reject('Text instead of integer money rejected',"INSERT INTO payment VALUES(9,1,'2026-09-12','invalid','cash','BAD')")
reject('Negative payment rejected',"INSERT INTO payment VALUES(9,1,'2026-09-12',-1,'cash','BAD')")
reject('Invalid order interval rejected',"INSERT INTO restoration_order VALUES(9,2,'2026-09-12','2026-09-01','closed','Test')")
reject('Unknown status rejected',"UPDATE restoration_order SET status='unknown' WHERE order_id=1")
reject('Referenced customer deletion rejected',"DELETE FROM customer WHERE customer_id=1")
reject('Duplicate order line rejected',"INSERT INTO order_work VALUES(1,1,1,1,100,'planned')")
con.execute('SAVEPOINT optional')
con.execute("INSERT INTO restoration_order VALUES(10,2,'2026-07-01','2026-07-10','cancelled','Без работ')")
check('Order without works and payments has zero balance',con.execute('SELECT agreed_kopecks,paid_kopecks,balance_kopecks FROM v_reception_balances WHERE order_id=10').fetchone()==(0,0,0))
con.execute("UPDATE order_work SET status='cancelled' WHERE order_id=1 AND line_no=2")
check('Cancelled work excluded from price',con.execute('SELECT agreed_kopecks FROM v_reception_balances WHERE order_id=1').fetchone()[0]==550000)
con.execute('ROLLBACK TO optional')
con.execute('RELEASE optional')
check('Restorer views do not expose customer contacts or money',all(not any(k in d[0] for k in ('phone','email','kopecks','customer')) for v in ('v_restorer_tasks','v_restorer_inspections') for d in con.execute('SELECT * FROM '+v).description))
con.commit()
out=ROOT/'verification'; out.mkdir(exist_ok=True)
for view in ('v_reception_orders','v_reception_balances','v_restorer_tasks','v_restorer_inspections'):
    cur=con.execute('SELECT * FROM '+view)
    with (out/(view+'.csv')).open('w',newline='') as f:
        w=csv.writer(f); w.writerow([d[0] for d in cur.description]); w.writerows(cur)
with sqlite3.connect(ROOT/'lab1.sqlite3') as target:
    con.backup(target)
(out/'checks.json').write_text(json.dumps({'sqlite_version':sqlite3.sqlite_version,'passed':len(results),'checks':results},ensure_ascii=False,indent=2)+'\n')
print(f'{len(results)} checks passed; lab1.sqlite3 and view CSV files generated')
