import pandas as pd
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
import time
import json

class StudentDataInput(BaseModel):
    file_path: str = Field(description="assets/student_grades.csv")

class LoadStudentDataTool(BaseTool):
    name: str = "load_student_data"
    description: str = "Загружает CSV с оценками студента"
    args_schema: Type[BaseModel] = StudentDataInput
    
    def _run(self, file_path: str = "assets/student_grades.csv") -> str:
        try:
            df = pd.read_csv(file_path)
            result = "Данные успеваемости студента:\n"
            for idx, row in df.iterrows():
                result += f"{idx+1}. Дисциплина: {row['Дисциплина']} | Оценка: {row['Оценка']} | Кредиты: {row['Кредиты']} | Семестр: {row['Семестр']}\n"
            return result
        except FileNotFoundError:
            return "Файл с данными студента не найден"
        except Exception as e:
            return f"Ошибка загрузки: {str(e)}"

class SupportResourcesInput(BaseModel):
    file_path: str = Field(description="assets/support_resources.txt")

class LoadSupportResourcesTool(BaseTool):
    name: str = "load_support_resources"
    description: str = "Загружает каталог университетских сервисов помощи"
    args_schema: Type[BaseModel] = SupportResourcesInput
    
    def _run(self, file_path: str = "assets/support_resources.txt") -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"Сервисы помощи:\n{content}"
        except FileNotFoundError:
            return "Файл с сервисами помощи не найден"

class AcademicRulesInput(BaseModel):
    file_path: str = Field(description="assets/academic_rules.txt")

class LoadAcademicRulesTool(BaseTool):
    name: str = "load_academic_rules"
    description: str = "Загружает правила академической задолженности"
    args_schema: Type[BaseModel] = AcademicRulesInput
    
    def _run(self, file_path: str = "assets/academic_rules.txt") -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"Правила академической задолженности:\n{content}"
        except FileNotFoundError:
            return """
            Стандартные правила:
            1. Оценка ниже 60 - академическая задолженность
            2. Пересдача возможна в течение 30 дней
            3. При повторной неудаче - индивидуальный план
            """

class MotivationLetterInput(BaseModel):
    letter_text: str = Field(description="Текст мотивационного письма")

class AnalyzeMotivationTool(BaseTool):
    name: str = "analyze_motivation"
    description: str = "Анализирует мотивационное письмо студента"
    args_schema: Type[BaseModel] = MotivationLetterInput
    
    def _run(self, letter_text: str) -> str:
        word_count = len(letter_text.split())
        if word_count < 50:
            return f"Письмо содержит {word_count} слов. Рекомендуется более подробное описание целей и проблем."
        return f"Письмо содержит {word_count} слов. Достаточно для анализа."

class RiskAssessmentInput(BaseModel):
    grades_summary: str = Field(description="Сводка по оценкам")

class RiskAssessmentTool(BaseTool):
    name: str = "assess_risk"
    description: str = "Оценивает риск отчисления на основе успеваемости"
    args_schema: Type[BaseModel] = RiskAssessmentInput
    
    def _run(self, grades_summary: str) -> str:
        low_grades = grades_summary.lower().count("2") + grades_summary.lower().count("неуд")
        if low_grades > 3:
            return "КРИТИЧЕСКИЙ РИСК: Множественные задолженности"
        elif low_grades > 1:
            return "СРЕДНИЙ РИСК: Требуется внимание"
        elif low_grades > 0:
            return "НИЗКИЙ РИСК: Можно исправить"
        return "РИСК ОТСУТСТВУЕТ"

class SearchSupportInput(BaseModel):
    query: str = Field(description="Поисковый запрос для поиска сервисов поддержки")

class SearchSupportTool(BaseTool):
    name: str = "search_support"
    description: str = "Ищет подходящие сервисы поддержки по ключевым словам"
    args_schema: Type[BaseModel] = SearchSupportInput
    
    def _run(self, query: str) -> str:
        results = []
        if "математика" in query.lower():
            results.append("- Центр математической поддержки")
        if "программирование" in query.lower():
            results.append("- Лаборатория программирования")
        if "психология" in query.lower():
            results.append("- Центр психологической поддержки")
        if "английский" in query.lower():
            results.append("- Языковой центр")
        if not results:
            results.append("- Консультационный центр университета")
        return "Найденные сервисы:\n" + "\n".join(results)

class HITLInput(BaseModel):
    question: str = Field(description="Вопрос к пользователю")

class HITLTool(BaseTool):
    name: str = "ask_human"
    description: str = """Задаёт вопрос пользователю и ждёт ответа.
    Используй когда нужно:
    1. Утверждение индивидуального плана восстановления
    2. Уточнение целей студента
    3. Выбор между вариантами поддержки
    4. Подтверждение коррекции рекомендаций"""
    args_schema: Type[BaseModel] = HITLInput
    
    def _run(self, question: str) -> str:
        hitl_data = {
            "question": question,
            "answered": False,
            "answer": None
        }
        with open("hitl_question.json", "w", encoding="utf-8") as f:
            json.dump(hitl_data, f, ensure_ascii=False, indent=2)
        
        while True:
            try:
                with open("hitl_question.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("answered", False):
                        return data.get("answer", "Пользователь не дал ответа")
            except:
                pass
            time.sleep(1)