import streamlit as st
import pandas as pd
import os
import json
import subprocess
import sys
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="План восстановления", layout="wide")

st.title("План восстановления студента")
st.markdown("---")

# ============================================================
# 1. РЕДАКТИРОВАНИЕ АГЕНТОВ
# ============================================================
st.header("1. Конфигурация агентов")

if "agent_configs" not in st.session_state:
    st.session_state.agent_configs = {
        "diagnostic": {
            "role": "Эксперт по диагностике успеваемости",
            "goal": "Выявить проблемные зоны в успеваемости",
            "backstory": "Ты анализируешь оценки студента."
        },
        "motivation": {
            "role": "Эксперт по мотивации",
            "goal": "Проанализировать мотивационное письмо",
            "backstory": "Ты анализируешь письмо студента."
        },
        "audit": {
            "role": "Специалист по уточнению",
            "goal": "Запросить недостающие данные",
            "backstory": "Ты задаёшь вопросы студенту."
        },
        "plan": {
            "role": "Академический консультант",
            "goal": "Сформировать план восстановления",
            "backstory": "Ты создаёшь индивидуальный план."
        }
    }

with st.expander("Редактировать агентов"):
    for agent in st.session_state.agent_configs:
        st.subheader(agent)
        st.session_state.agent_configs[agent]["role"] = st.text_input(
            f"{agent}_role", value=st.session_state.agent_configs[agent]["role"]
        )
        st.session_state.agent_configs[agent]["goal"] = st.text_input(
            f"{agent}_goal", value=st.session_state.agent_configs[agent]["goal"]
        )
        st.session_state.agent_configs[agent]["backstory"] = st.text_area(
            f"{agent}_back", value=st.session_state.agent_configs[agent]["backstory"], height=100
        )

st.markdown("---")

# ============================================================
# 2. ЗАГРУЗКА ФАЙЛОВ
# ============================================================
st.header("2. Входные данные")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Оценки (CSV)")
    grades_file = st.file_uploader("student_grades.csv", type=["csv"])
    if grades_file:
        df = pd.read_csv(grades_file)
        st.dataframe(df)
        if st.button("Сохранить оценки"):
            os.makedirs("assets", exist_ok=True)
            df.to_csv("assets/student_grades.csv", index=False)
            st.success("Сохранено")

    st.subheader("Мотивационное письмо (TXT)")
    letter_file = st.file_uploader("motivation_letter.txt", type=["txt"])
    if letter_file:
        text = letter_file.getvalue().decode("utf-8")
        st.text_area("Письмо", text, height=150)
        if st.button("Сохранить письмо"):
            os.makedirs("assets", exist_ok=True)
            with open("assets/motivation_letter.txt", "w", encoding="utf-8") as f:
                f.write(text)
            st.success("Сохранено")

with col2:
    st.subheader("Правила (TXT)")
    rules_file = st.file_uploader("academic_rules.txt", type=["txt"])
    if rules_file:
        text = rules_file.getvalue().decode("utf-8")
        st.text_area("Правила", text, height=150)
        if st.button("Сохранить правила"):
            os.makedirs("assets", exist_ok=True)
            with open("assets/academic_rules.txt", "w", encoding="utf-8") as f:
                f.write(text)
            st.success("Сохранено")

    st.subheader("Сервисы помощи (TXT)")
    support_file = st.file_uploader("support_resources.txt", type=["txt"])
    if support_file:
        text = support_file.getvalue().decode("utf-8")
        st.text_area("Сервисы", text, height=150)
        if st.button("Сохранить сервисы"):
            os.makedirs("assets", exist_ok=True)
            with open("assets/support_resources.txt", "w", encoding="utf-8") as f:
                f.write(text)
            st.success("Сохранено")

st.markdown("---")

# ============================================================
# 3. ЗАПУСК
# ============================================================
st.header("3. Запуск")

model = st.selectbox("Модель", [
    "gemini/gemini-3.1-flash-lite-preview",
    "gemini/gemini-2.5-flash-lite"
])

if st.button("ЗАПУСТИТЬ", type="primary", use_container_width=True):
    # Очищаем старые файлы
    for f in ["crew_result.json", "hitl_question.json"]:
        if os.path.exists(f):
            os.remove(f)
    
    config = {
        "model_name": model,
        "verbose": True,
        "agent_configs": st.session_state.agent_configs
    }
    
    with open("temp_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    subprocess.Popen([sys.executable, "crew.py"])
    st.success("Запущено! Обновите страницу через 5-10 секунд")
    st.rerun()

st.markdown("---")

# ============================================================
# 4. HITL (есть вопрос)
# ============================================================
hitl_file = "hitl_question.json"
if os.path.exists(hitl_file):
    try:
        with open(hitl_file, "r", encoding="utf-8") as f:
            hitl_data = json.load(f)
        
        if not hitl_data.get("answered", False):
            st.header("HITL - Требуется ответ")
            st.warning(hitl_data.get("question", ""))
            
            answer = st.text_area("Ваш ответ:", height=100)
            
            if st.button("Отправить ответ", type="primary"):
                if answer.strip():
                    hitl_data["answer"] = answer
                    hitl_data["answered"] = True
                    with open(hitl_file, "w", encoding="utf-8") as f:
                        json.dump(hitl_data, f, ensure_ascii=False, indent=2)
                    st.success("Ответ отправлен!")
                    st.rerun()
    except:
        pass

# ============================================================
# 5. РЕЗУЛЬТАТ
# ============================================================
result_file = "crew_result.json"
if os.path.exists(result_file):
    try:
        with open(result_file, "r", encoding="utf-8") as f:
            result = json.load(f)
        
        st.header("Результат")
        st.success("План восстановления готов!")
        st.code(result.get("result", str(result)), language="text")
    except:
        with open(result_file, "r", encoding="utf-8") as f:
            st.code(f.read(), language="text")

# ============================================================
# ПРОМЕЖУТОЧНЫЕ РЕЗУЛЬТАТЫ
# ============================================================
for file, title in [
    ("diagnostic_result.txt", "Диагностика"),
    ("motivation_analysis.txt", "Анализ письма"),
    ("audit_result.txt", "Аудит")
]:
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
        if content.strip():
            with st.expander(title):
                st.code(content, language="text")