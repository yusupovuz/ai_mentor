import os
from dotenv import load_dotenv
from crewai import Agent,Task,Crew,Process,LLM
from langchain_groq import ChatGroq

load_dotenv()

my_llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)
researcher = Agent(
    role='Katta Python Tadqiqotchisi',
    goal='Dasturlash bo\'yicha eng aniq, chuqur va texnik to\'g\'ri ma\'lumotlarni topish',
    backstory='Sen 10 yillik tajribaga ega Python arxitektori va poydevor texnologiyalarini chuqur tushunadigan mutaxassissan.',
    verbose=True,  # Bu ularning nima o'ylayotganini terminalda ko'rsatib turadi
    allow_delegation=False,
    llm=my_llm
)


writer = Agent(
    role='Texnik Maqolalar Yozuvchisi',
    goal='Tadqiqotchi topgan ma\'lumotlarni Junior dasturchilarga sodda va chiroyli tushuntirib berish',
    backstory='Sen murakkab kodlarni oddiy odamlar tushunadigan tilda, hayotiy misollar bilan tushuntirib beruvchi iqtidorli ustozsan.',
    verbose=True,
    allow_delegation=False,
    llm=my_llm
)

task1 = Task(
    description='Python\'da "Decorator" (Dekorator) nima ekanligini, nima uchun kerakligini va qanday ishlashini aniq misollar bilan o\'rganib chiq.',
    expected_output='Decorator ishlash mantig\'i va 1 ta aniq qisqa kod misoli.',
    agent=researcher
)

task2 = Task(
    description='Tadqiqotchining ma\'lumotidan foydalanib, Junior dasturchilar uchun Decorator haqida qisqa, tushunarli, qiziqarli o\'zbek tilida tushuntirish yoz. O\'quvchini zeriktirmaslik uchun misollarni sodda qil.',
    expected_output='Qisqa, sodda tildagi maqola (Markdown formatida).',
    agent=writer
)

my_crew = Crew(
    agents=[researcher, writer],
    tasks=[task1, task2],
    process=Process.sequential  # Birma-bir ishlash: avval tadqiqotchi topadi, keyin yozuvchiga beradi
)

if __name__ == "__main__":
    print(" AI Jamoasi ishni boshladi... (Terminalni kuzatib turing)")
    result = my_crew.kickoff()
    
    print("\n=======================================================")
    print(" YAKUNIY NATIJA (Yozuvchining tayyorlagan ishi):")
    print("=======================================================\n")
    print(result)