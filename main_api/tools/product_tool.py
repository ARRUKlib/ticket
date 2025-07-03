# main_api/tools/product_tool.py

from main_api.db import get_connection

def get_product_info():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT name, brand, description, price FROM products LIMIT 5")
    rows = cursor.fetchall()
    conn.close()

    product_lines = []
    for row in rows:
        product_lines.append(
            f"{row['name']} ({row['brand']}): {row['description']} ราคา {row['price']} บาท"
        )

    return "\n".join(product_lines)
