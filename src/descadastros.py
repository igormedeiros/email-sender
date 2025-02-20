from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import pandas as pd
from pathlib import Path
from datetime import datetime

app = FastAPI()

EMAILS_FILE = "emails_treineinsite.xlsx"
UNSUBSCRIBE_FILE = "descadastros.csv"

def remove_from_xlsx(email: str) -> bool:
    """Remove email from xlsx file and add to unsubscribe list"""
    try:
        # Read the Excel file
        df = pd.read_excel(EMAILS_FILE)
        
        # Check if email exists
        if email.lower() not in df['email'].str.lower().values:
            return False
        
        # Remove the email (case insensitive)
        df = df[df['email'].str.lower() != email.lower()]
        
        # Save back to Excel
        df.to_excel(EMAILS_FILE, index=False)
        
        # Add to unsubscribe list
        unsubscribe_data = {
            'email': [email],
            'data_descadastro': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        }
        
        if Path(UNSUBSCRIBE_FILE).exists():
            pd.DataFrame(unsubscribe_data).to_csv(UNSUBSCRIBE_FILE, mode='a', header=False, index=False)
        else:
            pd.DataFrame(unsubscribe_data).to_csv(UNSUBSCRIBE_FILE, index=False)
            
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/descadastro", response_class=HTMLResponse)
async def descadastro(email: str):
    if not email:
        raise HTTPException(status_code=400, detail="Email parameter is required")
    
    success = remove_from_xlsx(email)
    
    if not success:
        return """
        <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1>Email não encontrado</h1>
                <p>O email informado não está em nossa lista.</p>
            </body>
        </html>
        """
    
    return """
    <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1>Descadastro realizado com sucesso!</h1>
            <p>Você foi removido de nossa lista de emails.</p>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)