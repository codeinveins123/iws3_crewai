# crew.py
import os
import sys
import io
import json
import time
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tasks.conditional_task import ConditionalTask
from tools import *
from dotenv import load_dotenv

load_dotenv()

os.environ["CREWAI_DISABLE_EMOJI"] = "true"
os.environ["CREWAI_DISABLE_VERBOSE_COLORS"] = "true"

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

LOG_FILE = "crew_output.log"
HITL_FILE = "hitl_question.json"
RESULT_FILE = "crew_result.json"
STATUS_FILE = "crew_status.json"

def set_status(status):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump({"status": status}, f)

def write_log(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} - {message}\n")

def load_config():
    try:
        with open("temp_config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

config = load_config()

if config:
    MODEL_NAME = config.get("model_name", "gemini/gemini-2.5-flash-lite")
    VERBOSE_MODE = config.get("verbose", True)
    AGENT_CONFIGS = config.get("agent_configs", {})
else:
    MODEL_NAME = "gemini/gemini-2.5-flash-lite"
    VERBOSE_MODE = True
    AGENT_CONFIGS = {}

def get_agent_config(agent_name: str, key: str, default: str) -> str:
    try:
        return AGENT_CONFIGS.get(agent_name, {}).get(key, default)
    except:
        return default

DIAGNOSTIC_ROLE = get_agent_config("diagnostic", "role", "Эксперт по диагностике успеваемости")
DIAGNOSTIC_GOAL = get_agent_config("diagnostic", "goal", "Выявить проблемные зоны в успеваемости студента")
DIAGNOSTIC_BACKSTORY = get_agent_config("diagnostic", "backstory", """Вы анализируете оценки студента.
Используйте load_student_data для получения данных.
Определите предметы с низкими оценками, тренды и риски.""")

MOTIVATION_ROLE = get_agent_config("motivation", "role", "Эксперт по мотивационным письмам")
MOTIVATION_GOAL = get_agent_config("motivation", "goal", "Проанализировать мотивационное письмо и цели студента")
MOTIVATION_BACKSTORY = get_agent_config("motivation", "backstory", """Вы анализируете мотивационное письмо.
Определите ясность целей, понимание проблем, готовность к изменениям.""")

PLAN_ROLE = get_agent_config("plan", "role", "Академический консультант")
PLAN_GOAL = get_agent_config("plan", "goal", "Сформировать реалистичный план восстановления")
PLAN_BACKSTORY = get_agent_config("plan", "backstory", """Вы формируете индивидуальный план восстановления.
Учитывайте диагностику успеваемости, цели студента, доступные ресурсы.
Рекомендуйте конкретные дисциплины, темп, консультации.""")

AUDIT_ROLE = get_agent_config("audit", "role", "Специалист по уточнению данных")
AUDIT_GOAL = get_agent_config("audit", "goal", "Запросить недостающую информацию у студента")
AUDIT_BACKSTORY = get_agent_config("audit", "backstory", """Вы запрашиваете уточнения.
Если письмо слишком общее - спросите конкретные цели.
Если нет данных о нагрузке - уточните занятость.""")

load_student = LoadStudentDataTool()
load_resources = LoadSupportResourcesTool()
load_rules = LoadAcademicRulesTool()
analyze_motivation = AnalyzeMotivationTool()
assess_risk = RiskAssessmentTool()
search_support = SearchSupportTool()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

llm = LLM(
    model=MODEL_NAME,
    api_key=GEMINI_API_KEY
)

diagnostic_agent = Agent(
    role=DIAGNOSTIC_ROLE,
    goal=DIAGNOSTIC_GOAL,
    backstory=DIAGNOSTIC_BACKSTORY,
    tools=[load_student, assess_risk],
    llm=llm,
    verbose=VERBOSE_MODE,
    allow_delegation=False
)

diagnostic_task = Task(
    description="""Используй инструмент load_student_data.
    Файл: assets/student_grades.csv
    
    Проанализируй успеваемость студента:
    1. Определи предметы с низкими оценками
    2. Выяви тренды
    3. Оцени риск отчисления
    
    Верни структурированный диагноз.""",
    expected_output="Список проблемных дисциплин, тренды, уровень риска",
    agent=diagnostic_agent,
    output_file="diagnostic_result.txt"
)

motivation_agent = Agent(
    role=MOTIVATION_ROLE,
    goal=MOTIVATION_GOAL,
    backstory=MOTIVATION_BACKSTORY,
    tools=[analyze_motivation],
    llm=llm,
    verbose=VERBOSE_MODE,
    allow_delegation=False
)

motivation_task = Task(
    description="""Прочитай файл assets/motivation_letter.txt и проанализируй мотивационное письмо студента.
    
    Определи:
    1. Чёткость целей
    2. Понимание проблем
    3. Готовность к изменениям
    
    Верни оценку письма.""",
    expected_output="Оценка письма, выявленные проблемы",
    agent=motivation_agent,
    output_file="motivation_analysis.txt"
)

def needs_clarification_condition(task_output) -> bool:
    if hasattr(task_output, 'raw'):
        output_str = str(task_output.raw)
    else:
        output_str = str(task_output)
    
    conditions = [
        "слишком общее" in output_str.lower(),
        "менее" in output_str.lower() and "слов" in output_str.lower(),
        "не указан" in output_str.lower(),
        "требуется уточнение" in output_str.lower()
    ]
    return any(conditions)

class HITLFileTool(BaseTool):
    name: str = "ask_human"
    description: str = "Задаёт вопрос пользователю через файл и ждёт ответа"
    
    def _run(self, question: str) -> str:
        hitl_data = {
            "question": question,
            "answered": False,
            "answer": None,
            "timestamp": time.time()
        }
        with open(HITL_FILE, "w", encoding="utf-8") as f:
            json.dump(hitl_data, f, ensure_ascii=False, indent=2)
        
        write_log(f"HITL: Вопрос отправлен - {question[:100]}...")
        
        while True:
            try:
                with open(HITL_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("answered", False):
                        write_log(f"HITL: Получен ответ - {data.get('answer', '')[:100]}...")
                        return data.get("answer", "Нет ответа")
            except:
                pass
            time.sleep(1)

hitl_tool = HITLFileTool()

audit_agent = Agent(
    role=AUDIT_ROLE,
    goal=AUDIT_GOAL,
    backstory=AUDIT_BACKSTORY,
    tools=[hitl_tool],
    llm=llm,
    verbose=VERBOSE_MODE,
    allow_delegation=False
)

audit_task = ConditionalTask(
    description="""Если мотивационное письмо слишком общее или не хватает данных:
    
    1. Используй ask_human с вопросом: "Пожалуйста, уточните ваши цели и текущую нагрузку"
    2. Запиши полученный ответ
    
    Если данных достаточно - просто верни "Уточнения не требуются".""",
    expected_output="Уточнённые данные или сообщение о достаточности информации",
    agent=audit_agent,
    context=[motivation_task],
    condition=needs_clarification_condition,
    output_file="audit_result.txt"
)

plan_agent = Agent(
    role=PLAN_ROLE,
    goal=PLAN_GOAL,
    backstory=PLAN_BACKSTORY,
    tools=[load_rules, load_resources, search_support, hitl_tool],
    llm=llm,
    verbose=VERBOSE_MODE,
    allow_delegation=False
)

plan_task = Task(
    description="""На основе диагностики и целей студента сформируй план восстановления.

    У тебя есть:
    - Диагностика успеваемости (diagnostic_task)
    - Анализ мотивации (motivation_task)
    - Уточнения от студента (audit_task)

    СНАЧАЛА сформируй план, а затем ОБЯЗАТЕЛЬНО выполни эти действия:

    Шаг 1: Используй инструмент ask_human с вопросом:
    "Утвердите индивидуальный план восстановления? (Ответьте ДА или НЕТ, и если НЕТ - что исправить)"

    Шаг 2: Дождись ответа от пользователя.

    Шаг 3: Если ответ ДА - выведи финальный план.
    Шаг 4: Если ответ НЕТ - уточни у пользователя, что нужно изменить, внеси правки и выведи исправленный план.

    Сформируй план в таком формате:
    1. Дисциплины для пересдачи
    2. Рекомендуемый темп
    3. Консультации и сервисы поддержки
    4. Конкретные ресурсы из каталога
    
    Верни финальный план.""",
    expected_output="Индивидуальный план восстановления с подтверждением",
    agent=plan_agent,
    context=[diagnostic_task, motivation_task, audit_task],
    output_file=RESULT_FILE
)

crew = Crew(
    agents=[diagnostic_agent, motivation_agent, audit_agent, plan_agent],
    tasks=[diagnostic_task, motivation_task, audit_task, plan_task],
    process=Process.sequential,
    verbose=VERBOSE_MODE
)

if __name__ == "__main__":
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    if os.path.exists(HITL_FILE):
        os.remove(HITL_FILE)
    
    write_log("Запуск Crew...")
    write_log(f"Модель: {MODEL_NAME}")
    write_log("="*50)

    set_status("running")
    
    try:
        result = crew.kickoff()
        set_status("finished")
        
        write_log("\n" + "="*50)
        write_log("ИНДИВИДУАЛЬНЫЙ ПЛАН ВОССТАНОВЛЕНИЯ:")
        write_log("="*50)
        write_log(str(result))
        write_log("="*50)
        
        write_log("Crew завершил работу")
        
    except Exception as e:
        set_status("error")
        write_log(f"Ошибка: {str(e)}")
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            f.write(f"Ошибка: {str(e)}")