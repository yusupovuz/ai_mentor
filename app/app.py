from fastapi import FastAPI,Depends,HTTPException
from pydantic import BaseModel,Field
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
import jwt
from datetime import datetime,timedelta,timezone
from app.db.database import engine,Base
from app.db import models
from sqlalchemy.orm import Session
import bcrypt
from app.db.database import session_local,engine
import os
from dotenv import load_dotenv
from groq import Groq
from fastapi.responses import StreamingResponse,HTMLResponse
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langsmith import traceable
from crewai import Agent,Task,Crew,Process,LLM

load_dotenv()

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

SECRET_KEY = 'secret99'
ALGORITM = 'HS256'

client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

class ChatMessage(BaseModel):
    text:str

class ResearcherRequest(BaseModel):
    topic:str

class UserCreate(BaseModel):
    username:str
    password:str=Field(...,max_length=72)

def get_password_hash(password:str):
    password_bytes = password.encode('utf-8')[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password:str, hashed_password:str):
    plain_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)

def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()

def create_jwt_token(data:dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({'exp':expire})
    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITM)
    return encoded_jwt


@app.get('/')
def read_root():
    with open('frontend/index.html','r',encoding='utf-8') as f:
        return HTMLResponse(content=f.read())

@app.post('/register')
def register(user:UserCreate,db:Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400,detail='Bu ism band, boshqa ism tanlang!')

    hashed_password = get_password_hash(user.password)

    new_user = models.User(username=user.username,hashed_password=hashed_password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {'message':'Tabriklaymiz ro\'yxatdan o\'tdingiz','user_id':new_user.id}

@app.post('/login')
def login(form_data:OAuth2PasswordRequestForm = Depends(),db:Session=Depends(get_db)):
    
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    if not user or not verify_password(form_data.password,user.hashed_password):
        raise HTTPException(status_code=401,detail='Login yoki parol xato!')
    
    token = create_jwt_token({'sub':user.username})
    return {'access_token':token,'token_type':'bearer'}

def get_current_user(token:str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token,SECRET_KEY,algorithms=ALGORITM)
        username:str = payload.get('sub')
        if username is None:
            raise HTTPException(status_code=401,detail='Token ichida ism yo\'q')
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401,detail='Tokendi vaqti tugagan')
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401,detail='Token xato yoki soxta!')

@app.post('/chat')
@traceable(name="AI_Mentor_RAG_Pipeline")
def send_message(
    message:ChatMessage,
    current_user:str=Depends(get_current_user),
    db:Session = Depends(get_db)

):
    try:

        user = db.query(models.User).filter(models.User.username == current_user).first()
        past_messages = db.query(models.Message).filter(models.Message.owner_id == user.id).order_by(models.Message.id.asc()).all()[-5:]

        search_results = vector_db.similarity_search(message.text,k=3)

        context_text = '\n\n'.join([doc.page_content for doc in search_results])

        system_prompt = f"""Sen tajribali va yordamga tayyor AI Mentorsan. 
O'zbek tilida qisqa va lo'nda javob ber. 
Foydalanuvchi savoliga javob berishda QAT'IY RAVISHDA quyidagi kitobdan olingan ma'lumotlarga asoslan:

MA'LUMOTLAR:
{context_text}
"""
        
        groq_messages = [
            {"role": "system", "content": system_prompt}
        ]
        

        for msg in past_messages:
            groq_messages.append({'role':'user','content':msg.user_question})
            groq_messages.append({'role':'assistant','content':msg.ai_reply})


        groq_messages.append({'role':'user','content':message.text})

        chat_completion = client.chat.completions.create(
            messages=groq_messages,
            model='llama-3.3-70b-versatile',
            stream=True
        )

        def generate():
            full_reply = ""
            for chunk in chat_completion:
                if chunk.choices[0].delta.content is not None:
                    word = chunk.choices[0].delta.content
                    full_reply += word
                    yield word
            new_msg = models.Message(
                user_question=message.text,
                ai_reply=full_reply,
                owner_id=user.id
            )
            db.add(new_msg)
            db.commit()

        # ai_reply = chat_completion.choices[0].message.content
        
        # db.refresh(new_msg)

        # return {
        #     'user':current_user,
        #     'question':message.text,
        #     'bot_reply':ai_reply,
        #     'message_id':new_msg.id
        # }
        return StreamingResponse(generate(),media_type='text/event-stream')
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"Ai bilan bog'lanishda xatolik: {str(e)}")
    
@app.get('/history')
def get_chat_history(current_user: str = Depends(get_current_user),db:Session=Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == current_user).first()

    all_messages = db.query(models.Message).filter(models.Message.owner_id == user.id).order_by(models.Message.id.asc()).all()

    return {'user':current_user,'history':all_messages}

current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir,'chroma_db')

embeddings = HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')
vector_db = Chroma(persist_directory=db_path,embedding_function=embeddings)


@app.post('/deep-research')
def run_research_crew(
    request:ResearcherRequest,
    current_user: str=Depends(get_current_user)
):
    my_llm = LLM(
        model='groq/llama-3.3-70b-versatile',
        api_key=os.getenv('GROQ_API_KEY')
    )
    researcher = Agent(
        role='Katta Tadqiqotchi',
        goal=f'"{request.topic}" mavzusida eng aniq va chuqur texnik ma\'lumotlarni topish',
        backstory='Sen katta tajribaga ega arxitektor va mutaxassissan.',
        verbose=True,
        allow_delegation=False,
        llm=my_llm
    )

    writer = Agent(
        role='Texnik Maqolalar Yozuvchisi',
        goal='Tadqiqotchi topgan ma\'lumotlarni sodda va chiroyli tushuntirib berish',
        backstory='Sen murakkab narsalarni oddiy odamlar tushunadigan tilda tushuntiruvchi ustozsan.',
        verbose=True,
        allow_delegation=False,
        llm=my_llm
    )
    task1 = Task(
        description=f'"{request.topic}" nima ekanligini, nima uchun kerakligini va qanday ishlashini o\'rganib chiq.',
        expected_output='Mavzuning ishlash mantig\'i va aniq misollar.',
        agent=researcher
    )

    task2 = Task(
        description='Tadqiqotchining ma\'lumotidan foydalanib, yangi o\'rganayotganlar uchun qisqa va tushunarli o\'zbek tilida maqola yoz.',
        expected_output='Qisqa, sodda tildagi maqola (Markdown formatida).',
        agent=writer
    )

    my_crew = Crew(
        agents=[researcher, writer],
        tasks=[task1, task2],
        process=Process.sequential
    )

    # Natijani olamiz (bu jarayon biroz vaqt oladi, chunki botlar o'ylaydi)
    result = my_crew.kickoff()
    
    # Natijani mijozga API orqali qaytaramiz
    return {"topic": request.topic, "article": str(result)}