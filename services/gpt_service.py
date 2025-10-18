import os
import aiohttp
import json
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class GPTService:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
        
    async def generate_post_text(self, facts: List[Dict], object_type: str, object_name: str) -> Dict[str, Any]:
        """Генерация текста поста через GPT"""
        
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return await self._generate_fallback_text(facts, object_type, object_name)
        
        # Формируем сводку фактов
        facts_summary = "\\n".join([
            f"- {fact.get('content', '')} ({fact.get('year', 'без даты')})" 
            for fact in facts[:5]
        ])
        
        prompt = f"""
        Напиши интересный пост для Telegram об {object_type} "{object_name}" в Москве.
        Используй эти факты:
        {facts_summary}

        Требования:
        - Объём: 800-1000 символов
        - Структура: завлекающее начало, 2-3 абзаца фактов, интересное завершение
        - Стиль: живой, увлекательный, без кликбейта
        - Без эмодзи и хештегов
        """
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-3.5-turbo",  # Используем более доступную модель
            "messages": [
                {
                    "role": "system", 
                    "content": "Ты пишешь увлекательные исторические посты о Москве для широкой аудитории."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        text = result['choices'][0]['message']['content'].strip()
                        
                        return {
                            "success": True,
                            "text": text,
                            "character_count": len(text),
                            "model": "gpt-3.5-turbo"
                        }
                    else:
                        return await self._generate_fallback_text(facts, object_type, object_name)
                        
        except Exception:
            return await self._generate_fallback_text(facts, object_type, object_name)
    
    async def _generate_fallback_text(self, facts: List[Dict], object_type: str, object_name: str) -> Dict[str, Any]:
        """Создание текста без GPT"""
        text = f"{object_name} - {object_type} с богатой историей.\\n\\n"
        
        # Добавляем факты
        for i, fact in enumerate(facts[:3], 1):
            text += f"{fact.get('content', '')}\\n"
        
        text += "\\nИсторическая Москва хранит множество удивительных историй!"
        
        return {
            "success": True,
            "text": text,
            "character_count": len(text),
            "model": "fallback"
        }
    
    async def generate_complete_post(self, object_data: Dict, facts: List[Dict]) -> Dict[str, Any]:
        """Генерация полного поста с текстом"""
        object_type_map = {
            "district": "район",
            "street": "улица",
            "building": "дом"
        }
        
        object_type_ru = object_type_map.get(object_data['type'], object_data['type'])
        object_name = object_data.get('name', object_data.get('address', ''))
        
        # Генерируем текст
        text_result = await self.generate_post_text(facts, object_type_ru, object_name)
        
        # План изображения
        image_style = "coat_of_arms" if object_data['type'] == "district" else "architectural_watercolor_sempe"
        
        return {
            "object_type": object_data['type'],
            "object_name": object_name,
            "text": text_result['text'],
            "character_count": text_result['character_count'],
            "generation_model": text_result.get('model', 'unknown'),
            "facts_used": len(facts),
            "image_style": image_style
        }
    
    def _get_image_style(self, object_type: str) -> str:
        """Определение стиля изображения"""
        return "coat_of_arms" if object_type == "district" else "architectural_watercolor_sempe"
