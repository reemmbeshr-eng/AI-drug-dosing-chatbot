import pandas as pd
import requests
import re
import base64


class DosageLogic:
    """
    Core logic class for:
    - Loading and cleaning drug dosage data from Excel
    - Identifying drug names from images using a vision LLM
    - Calculating accurate pediatric dosages
    - Parsing indication text into structured sections
    - Querying a local LLM (Ollama)
    """

    def __init__(self, file_path: str):
        """
        Initialize the DosageLogic object.

        Parameters
        ----------
        file_path : str
            Path to the Excel file containing drug data.
        """
        self.file_path = file_path
        self.df = None

    def load_data(self):
        """
        Load the Excel file into a Pandas DataFrame and clean column names.

        Returns: Status flag and descriptive message.
        """
        try:
            self.df = pd.read_excel(self.file_path)
            self.df.columns = self.df.columns.str.strip()
            return True, "Data loaded successfully"
        except Exception as e:
            return False, f"Load Error: {str(e)}"

    def identify_drug_from_image(self, image_bytes: bytes) -> str:
        import base64
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        url = "http://127.0.0.1:11434/api/generate"
        
        payload = {
            "model": "llava",
            "prompt": "Identify the drug name. Reply with the GENERIC NAME ONLY. No sentences.",
            "images": [image_base64],
            "stream": False
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            res_text = response.json().get("response", "").strip()

            # clean text
            clean_name = re.sub(r'[^a-zA-Z\s]', '', res_text).strip()
            
            # take first word only
            if clean_name:
                return clean_name.split()[0]
            return ""
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            print(f"DEBUG: Response from AI is: {res_text}")
            return ""

    def calculate_dosage(
        self,
        weight: float,
        dose_value: float,
        unit: str,
        frequency_text: str,
        concentration: float
    ) -> dict:
        """
        Perform dosage calculations based on weight, unit, and frequency.

        Parameters :       
        weight :  Patient weight in kilograms.
        dose_value :  Prescribed dose value.
        unit : Dose unit (e.g. "mg/kg/day" or "mg/kg/dose").
        frequency_text :Frequency description (e.g. "Every 8 hours").
        concentration : Drug concentration (mg/ml).
        Returns: Calculated dosage values per dose and per day.
        """
        try:
            freq_map = {
                "Every 6 hours": 4,
                "Every 8 hours": 3,
                "Every 12 hours": 2,
                "Every 24 hours": 1
            }

            times_per_day = freq_map.get(frequency_text, 1)

            if unit == "mg/kg/day":
                total_mg_per_day = dose_value * weight
                mg_per_dose = total_mg_per_day / times_per_day
            else:  # mg/kg/dose
                mg_per_dose = dose_value * weight
                total_mg_per_day = mg_per_dose * times_per_day

            ml_per_dose = mg_per_dose / concentration

            return {
                "mg_per_dose": round(mg_per_dose, 2),
                "ml_per_dose": round(ml_per_dose, 2),
                "total_daily_mg": round(total_mg_per_day, 2),
                "times_per_day": times_per_day
            }

        except Exception:
            return None

    def parse_indications(self, text: str) -> dict:
        """parse indications from text"""
        if pd.isna(text) or not str(text).strip():
            return {"General Info": "No data available"}

        text = str(text).strip()
        sections = {}

        # 1 try find bold words with **
        bold_title_pattern = re.compile(r"\*\*(.+?)\*\*")
        matches = list(bold_title_pattern.finditer(text))

        if matches:
            for i, match in enumerate(matches):
                title = match.group(1).strip()
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                content = text[start:end].strip(" \n:-")
                sections[title] = content
        else:
            
            items = re.split(r'\. (?=[A-Z])', text) 
             
            # clean items  
            formatted_text = ""
            for item in items:
                clean_item = item.strip()
                if clean_item:
                    if not clean_item.endswith('.'):
                        clean_item += '.'
                    formatted_text += f"* {clean_item}\n\n"
            
            sections["Dosage & Indications"] = formatted_text

        return sections

   def search_drug(self, drug_name: str):
        if self.df is None or not drug_name:
            return pd.DataFrame()

        search_term = str(drug_name).lower().strip()
        
        first_word = search_term.split()[0] if search_term else ""

        mask = self.df["Generic Name"].str.lower().str.contains(first_word, na=False)
        return self.df[mask]
    def query_ollama(self, prompt: str, model: str = "llama3") -> str:
        """
        Query a local Ollama language model.
        Parameters : 
        prompt : Input prompt for the model.
        model : Ollama model name.

        Returns : Model response.
        """
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            return response.json().get("response", "No response from model.")
        except Exception as e:
            return f"AI Error: Ensure Ollama is running locally. ({str(e)})"