import sqlite3
def read_all_data(db_file):
    table_name = "courses"
    """
    Reads all rows from the specified table in the given SQLite database.
    
    :param db_file: Name of the database file (in the same folder)
    :param table_name: Name of the table to read
    :return: Tuple of (columns, rows)
    """
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    try:
        query = f"SELECT * FROM {table_name} where credits <= 4;"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        # Get column names from cursor.description
        columns = [desc[0] for desc in cursor.description]
        
        return columns, rows
    
    except sqlite3.Error as e:
        print("An error occurred:", e)
        return [], []
    
    finally:
        conn.close()


# Example usage
columns, data = read_all_data("sample_university.db")

# Print column names
print(" | ".join(columns))
for row in data:
    for col in row:
        print(col, end="   ")
    print()   # this already moves to the next line
