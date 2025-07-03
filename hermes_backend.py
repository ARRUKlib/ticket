from fastapi import FastAPI
from pydantic import BaseModel
import logging
from llama_cpp import Llama

class GenerateRequest(BaseModel):
    question: str
    context: str = ""

app = FastAPI()
logging.basicConfig(level=logging.INFO)

llm = Llama(
    model_path="./models/DeepHermes-3-Llama-3-8B-q6.gguf",
    n_gpu_layers=-1,
    n_ctx=4096,
    chat_format="chatml"
)

@app.post("/generate")
def generate_answer(req: GenerateRequest):
    prompt = [
        {
            "role": "system",
            "content": (
                "คุณคือ Thunjai ผู้ช่วย AI ของบริษัท WTC Computer ที่ต้องตอบคำถามให้ชัดเจน กระชับ ไม่เกิน 6 บรรทัด "
                "หากคำถามเกินขอบเขตหรือมีแนวโน้มเป็นปัญหาซับซ้อน ควรแนะนำให้ส่งต่อเจ้าหน้าที่ และอย่าตอบเยิ่นเย้อ"
            )
        },
        {
            "role": "user",
            "content": f"{req.question}\n\nข้อมูลเพิ่มเติม:\n{req.context}"
        }
    ]

    logging.info("[Hermes] Received question: %s", req.question)
    if req.context:
        logging.info("[Hermes] With context: %s", req.context[:200])

    res = llm.create_chat_completion(messages=prompt)
    answer = res["choices"][0]["message"]["content"]
    logging.info("[Hermes] Response: %s", answer)
    return {"answer": answer}
