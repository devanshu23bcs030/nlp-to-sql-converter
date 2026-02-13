from fastapi import APIRouter
router = APIRouter()
from functions import manualFunction # Your existing manual function
from globals import session_map
import sqlite3
import os                     # To read environment variables
from dotenv import load_dotenv # To load .env file
import google.generativeai as genai # Gemini API

# Load environment variables from .env file
load_dotenv()

# --- AI Function Setup ---
# Configure Gemini API using the key from .env
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Warning: GOOGLE_API_KEY not found in .env file. AI function will fail.")
        # Attempt to configure anyway, but API calls will likely fail later.
        genai.configure(api_key="MISSING_KEY") # Use a placeholder
    else:
        genai.configure(api_key=api_key)
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    # Handle the case where configuration itself fails catastrophically
    # You might want to prevent the app from starting or disable AI features
    # For now, we'll let it proceed, but AI calls will fail.
    genai.configure(api_key="CONFIGURATION_ERROR")


# --- Helper to get schema just for AI prompt ---
def get_db_schema_for_ai(db_path: str):
    """Gets table names and column names for the AI prompt."""
    schema = {}
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for (table_name,) in tables:
            if table_name.startswith('sqlite_'): continue
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns_data = cursor.fetchall()
            columns = [col[1] for col in columns_data]
            schema[table_name] = columns
    except Exception as e:
        print(f"Error getting schema for AI: {e}")
    finally:
        if conn:
            conn.close()
    return schema

# --- AI Function Definition (AttributeError fix) ---
def ai_function(nlp_text: str, db_path: str) -> str:
    """
    Converts a natural language string into an SQLite3 SQL query using Google's Gemini API,
    providing database schema as context.
    """
    # Check if API key might be missing/invalid from configuration step
    # Note: This is a basic check; the actual API call is the definitive test.
    current_key = os.getenv("GOOGLE_API_KEY") # Re-check env var directly if needed
    if not current_key or current_key in ["MISSING_KEY", "CONFIGURATION_ERROR"]:
         print("AI Function: API Key seems missing or invalid based on initial setup.")
         # You could return an error here, or let the API call fail below.
         # For robustness, let's allow the attempt and catch the specific API error.
         # return "AI_ERROR: Gemini API key not configured correctly."

    # Get schema to help the AI
    schema_details = get_db_schema_for_ai(db_path)
    schema_prompt_part = "The database has the following tables and columns:\n"
    if not schema_details:
         schema_prompt_part = "Could not retrieve database schema.\n"
    else:
        for table, columns in schema_details.items():
            schema_prompt_part += f"- {table}: ({', '.join(columns)})\n"

    prompt = f"""
    You are an expert natural language to SQLite3 SQL translator.
    {schema_prompt_part}
    Convert the following natural language instruction into a single, valid SQLite3 SQL query.
    Only provide the SQL query, nothing else. Do not wrap it in markdown or backticks.

    Instruction: "{nlp_text}"
    SQL Query:
    """

    try:
        # Instantiate the model first, then generate content
        model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
        response = model.generate_content(prompt)

        # Basic cleanup
        sql_query = response.text.strip()
        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()

        if not sql_query or len(sql_query) < 5:
             raise ValueError("Generated query is empty or too short.")
        if not sql_query.endswith(';'):
            sql_query += ';'

        print(f"🧠 AI Generated SQL: {sql_query}")
        return sql_query

    # --- Catch specific API-related errors if possible ---
    # (The exact exception type might vary depending on the library version)
    # except google.api_core.exceptions.PermissionDenied as e:
    #     print(f"❌ AI Error - Permission Denied (Check API Key): {e}")
    #     return f"AI_ERROR: Permission Denied. Check your API key and ensure the API is enabled."
    # except google.api_core.exceptions.NotFound as e:
    #      print(f"❌ AI Error - Model Not Found: {e}")
    #      return f"AI_ERROR: Model name might be incorrect or unavailable."
    except Exception as e:
        # General catch-all for other errors (network, parsing, etc.)
        print(f"❌ AI Error: {e}")
        # Check if the error message indicates an API key issue
        if "api key" in str(e).lower():
             return f"AI_ERROR: Invalid API Key or API not enabled: {e}"
        return f"AI_ERROR: Error generating query: {e}"


# --- Function to get full details for the frontend browser ---
# (This remains unchanged)
def get_full_db_details(db_path: str):
    db_details = {}
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for (table_name,) in tables:
            if not table_name.replace('_', '').isalnum(): continue
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns_data = cursor.fetchall()
            schema_columns = [{"name": col[1], "type": col[2]} for col in columns_data]
            content_headers = [col[1] for col in columns_data]
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
            db_details[table_name] = {
                "schema": schema_columns,
                "content": {"headers": content_headers, "rows": rows}
            }
    except Exception as e: return {"error": str(e)}
    finally:
        if conn: conn.close()
    return {"db_details": db_details}

# --- Main API Endpoint ---
# (Logic remains the same as before, calls the updated ai_function)
# ... (Keep imports and other functions like ai_function, get_db_schema_for_ai, get_full_db_details) ...

@router.get('/process')
async def process_query(session_token: str, query: str):
    token = session_token
    if token not in session_map:
        return {"error": "Invalid session. Please re-upload the database."}

    db_path = session_map[token]

    if query == "__GET_SCHEMA_AND_CONTENT__":
        details = get_full_db_details(db_path)
        # For this special query, we don't need SQL, just the result
        return {"executed_sql": None, "result": details}

    # --- NLP Query Processing Flow ---
    sql_to_execute = "unknown error" # Default value
    origin = "manual" # Track where the SQL came from

    # 1. Try Manual Function
    try:
        manual_result_list = manualFunction.nl2sql([query])
        sql_to_execute = manual_result_list[0]
    except Exception as e:
        print(f"Manual function error: {e}")
        sql_to_execute = "unknown error"

    # 2. If Manual Function failed, try AI Function
    if sql_to_execute == "unknown error":
        origin = "ai" # Mark as AI generated
        print(f"Manual function failed for: '{query}'. Trying AI...")
        try:
            sql_to_execute = ai_function(query, db_path)
        except Exception as e:
           print(f"AI function execution error: {e}")
           # Return error and null SQL
           return {"executed_sql": None, "error": f"AI function failed during execution: {e}"}

        if sql_to_execute.startswith("AI_ERROR:"):
             # Return error and null SQL
             return {"executed_sql": None, "error": sql_to_execute}

    # 3. Execute the SQL (from either manual or AI)
    conn = None
    result_data = None # Store the data/message here
    error_message = None # Store potential errors here

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"Executing SQL ({origin}): {sql_to_execute}")
        cursor.execute(sql_to_execute)

        is_select_query = sql_to_execute.strip().lower().startswith("select")

        if is_select_query:
            headers = [description[0] for description in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            result_data = {"headers": headers, "rows": rows} # Store data object
        else:
            conn.commit()
            result_data = f"{cursor.rowcount} rows affected." # Store message string

    except sqlite3.Error as e:
        error_message = f"Database Error: {e}"
        print(f"❌ Database Error: {e} for SQL: {sql_to_execute}")
    except Exception as e:
        error_message = f"Execution Error: {e}"
        print(f"❌ Execution Error: {e} for SQL: {sql_to_execute}")
    finally:
        if conn:
            conn.close()

    # --- Return Executed SQL and Result/Error ---
    if error_message:
        # If there was an execution error, return it instead of data
        return {"executed_sql": sql_to_execute, "result": error_message}
    else:
        # Otherwise, return the successful result
        return {"executed_sql": sql_to_execute, "result": result_data}