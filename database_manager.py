import sqlite3

class DatabaseManager:
    def __init__(self, db_name="supermarket_sales.db"):
        """
        Construtor da classe: cria a conexão e chama a criação da tabela (caso não exista).
        """
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        print(self.conn.execute("""SELECT name FROM sqlite_master
                                        WHERE type='table'
                                        ORDER BY name;"""))
        
        # self.create_table()

    def create_table(self):
        """
        Cria a tabela supermarket_sales caso ela não exista.
        """
        query = """
            CREATE TABLE IF NOT EXISTS supermarket_sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Product_line TEXT,
                Date TEXT,
                Unit_price REAL,
                Quantity INTEGER,
                gross_income REAL
            );
        """
        self.conn.execute(query)
        self.conn.commit()

    def insert_data(self, Product_line, Date, Unit_price, Quantity, gross_income):
        """
        Insere um novo registro na tabela supermarket_sales.
        """
        query = """
            INSERT INTO supermarket_sales (Product_line, Date, Unit_price, Quantity, gross_income)
            VALUES (?, ?, ?, ?, ?);
        """
        self.conn.execute(query, (Product_line, Date, Unit_price, Quantity, gross_income))
        self.conn.commit()

    def get_all_data(self):
        """
        Retorna todos os registros da tabela supermarket_sales.
        """
        query = "SELECT * FROM supermarket_sales;"
        cursor = self.conn.execute(query)
        data = cursor.fetchall()
        return data

    def update_data(self, record_id, Product_line, Date, Unit_price, Quantity, gross_income):
        """
        Atualiza um registro específico na tabela supermarket_sales.
        """
        query = """
            UPDATE supermarket_sales
            SET Product_line = ?,
                Date = ?,
                Unit_price = ?,
                Quantity = ?,
                gross_income = ?
            WHERE id = ?;
        """
        self.conn.execute(query, (Product_line, Date, Unit_price, Quantity, gross_income, record_id))
        self.conn.commit()

    def delete_data(self, record_id):
        """
        Deleta um registro específico na tabela supermarket_sales.
        """
        query = """
            DELETE FROM supermarket_sales
            WHERE id = ?;
        """
        self.conn.execute(query, (record_id,))
        self.conn.commit()

    def __del__(self):
        """
        Fecha a conexão com o banco de dados quando o objeto é destruído.
        """
        self.conn.close()