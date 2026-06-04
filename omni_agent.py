import os
import json
import requests
import time
import pandas as pd
from urllib.parse import quote  
from datetime import datetime
from openai import OpenAI  
from docx import Document
from pptx import Presentation
from pptx.util import Inches
from fpdf import FPDF

# ==========================================================
# ⚙️ HUGGING FACE STABLE ENDPOINT ROUTING
# ==========================================================
HF_MODEL_NAME = "google/gemma-4-31b-it" 

class UniversalAgent:
    def __init__(self, api_key):
        # We target the standard inference base URL
        # Hugging Face serverless handles routing using the model string parameter
        self.client = OpenAI(
            base_url="https://api-inference.huggingface.co/v1",
            api_key=api_key
        )
        self.model = HF_MODEL_NAME
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def get_text(self, prompt, is_json=False):
        try:
            messages = []
            if is_json:
                messages.append({
                    "role": "system", 
                    "content": "<|think|> You are a strict JSON structural engine. Output raw JSON ONLY. No formatting markdown backticks (such as ```json). Drop all introduction text or conversational pleasantries."
                })
            messages.append({"role": "user", "content": prompt})

            # CRITICAL: We explicitly set a larger timeout limit (e.g., 60.0s) 
            # to let the massive 31B model load up in the background without throwing connection errors.
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"} if is_json else None,
                temperature=0.1 if is_json else 0.7,
                extra_headers={"X-Wait-For-Model": "true"}  # Tells HF to wait for the model to load
            )
            return response.choices[0].message.content
        except Exception as e:
            return "{}" if is_json else f"Error: {e}"

    # --- 🎨 IMAGE GEN (FOR PPT/PDF) ---
    def _generate_temp_image(self, prompt):
        try:
            encoded_prompt = quote(prompt)
            url = f"[https://gen.pollinations.ai/image/](https://gen.pollinations.ai/image/){encoded_prompt}?width=800&nologo=true"
            r = self.session.get(url, timeout=15)
            if r.status_code == 200:
                temp_name = f"temp_{int(time.time())}.jpg"
                with open(temp_name, "wb") as f:
                    f.write(r.content)
                return temp_name
            return None
        except Exception as e: 
            print(f"DEBUG: Image Error - {e}")
            return None

    # --- 📄 PDF GENERATION ---
    def create_pdf(self, topic, filename):
        try:
            if not filename.endswith(".pdf"): filename = f"{topic.replace(' ', '_')}_{int(time.time())}.pdf"
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("helvetica", 'B', 16)
            pdf.cell(0, 10, txt=topic.upper(), ln=True, align='C')
            
            img = self._generate_temp_image(f"A professional visual representing {topic}")
            if img:
                pdf.image(img, x=10, y=30, w=180)
                pdf.set_y(150)
                os.remove(img)

            pdf.set_font("helvetica", size=12)
            raw_text = self.get_text(f"Write a comprehensive 3-paragraph report on {topic}")
            clean_text = raw_text.encode('latin-1', 'ignore').decode('latin-1')
            pdf.multi_cell(0, 10, txt=clean_text)
            
            pdf.output(filename)
            return {"message": f"✅ PDF Document Created: {topic}", "file_path": filename}
        except Exception as e: return {"message": f"❌ PDF Error: {e}", "file_path": None}

    # --- 📽️ PPT GENERATION ---
    def create_ppt(self, topic, filename, slides=3):
        try:
            if not filename.endswith(".pptx"): filename = f"{topic.replace(' ', '_')}_{int(time.time())}.pptx"
            prs = Presentation()
            for i in range(slides):
                slide = prs.slides.add_slide(prs.slide_layouts[1])
                slide.shapes.title.text = f"{topic} - Slide {i+1}"
                slide.placeholders[1].text = self.get_text(f"Generate presentation bullet points for {topic}, part {i+1}")
            prs.save(filename)
            return {"message": f"✅ Presentation Slides Created: {topic}", "file_path": filename}
        except Exception as e: return {"message": f"❌ PPT Error: {e}", "file_path": None}

    # --- 📊 EXCEL GENERATION ---
    def create_excel(self, topic, filename):
        try:
            if not filename.endswith(".xlsx"): filename = f"{topic.replace(' ', '_')}_{int(time.time())}.xlsx"
            raw_text = self.get_text(f"Provide data tables about '{topic}'. Structure output precisely like this JSON example template: {{\"cols\":[\"Header1\",\"Header2\"],\"rows\":[[\"Value1\",\"Value2\"]]}}", is_json=True)
            data = json.loads(raw_text)
            df = pd.DataFrame(data['rows'], columns=data['cols'])
            df.to_excel(filename, index=False)
            return {"message": f"✅ Excel Spreadsheet Created: {topic}", "file_path": filename}
        except Exception as e: return {"message": f"❌ Excel Error: {e}", "file_path": None}

    # --- 📝 WORD GENERATION ---
    def create_word(self, topic, filename):
        try:
            if not filename.endswith(".docx"): filename = f"{topic.replace(' ', '_')}_{int(time.time())}.docx"
            doc = Document()
            doc.add_heading(topic, 0)
            doc.add_paragraph(self.get_text(f"Write a report about {topic}"))
            doc.save(filename)
            return {"message": f"✅ Word Document Created: {topic}", "file_path": filename}
        except Exception as e: return {"message": f"❌ Word Error: {e}", "file_path": None}

    # --- 🧠 DISPATCHER ---
    def handle_request(self, user_prompt):
        brain_p = f"""
        User Prompt: "{user_prompt}"
        Determine the file output goal. Options: pdf, ppt, excel, word, text.
        Return raw JSON only matching this template: {{"tool": "selected_option", "subject": "the_subject", "file": "filename"}}
        """
        try:
            raw_res = self.get_text(brain_p, is_json=True)
            res = json.loads(raw_res)
            
            t = res.get('tool', 'text')
            s = res.get('subject', user_prompt)
            f = res.get('file', 'output')

            if t == 'pdf': result = self.create_pdf(s, f)
            elif t == 'ppt': result = self.create_ppt(s, f)
            elif t == 'excel': result = self.create_excel(s, f)
            elif t == 'word': result = self.create_word(s, f)
            else: 
                result = {"message": self.get_text(user_prompt), "file_path": None}

            return json.dumps(result)
            
        except (json.JSONDecodeError, Exception):
            chat_reply = self.get_text(user_prompt)
            return json.dumps({"message": chat_reply, "file_path": None})
