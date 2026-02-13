import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key="YOUR_API_KEY")

def ai_function(nlp_text: str) -> str:
    """
    Converts a natural language string into an SQLite3 SQL query using Google's Gemini API.
    """
    prompt = f"""
    Convert the following natural language instruction into a valid SQLite3 SQL query.
    Only provide the SQL query, nothing else.

    Instruction: "{nlp_text}"
    """

    try:
        # Generate SQL query using Gemini API
        response = genai.generate_content(
            model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025') ,  # Use the appropriate model
            contents=[{"text": prompt}]
        )
        sql_query = response.result[0].text.strip()
        return sql_query
    except Exception as e:
        return f"Error generating query: {e}"
