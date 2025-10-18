import os
import aiohttp
import json
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class PerplexityService:
    def __init__(self):
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        self.base_url = "https://api.perplexity.ai"
        
    async def get_historical_facts(self, object_type: str, name: str, location: str = "Москва") -> Dict[str, Any]:
        """Получение исторических фактов через Perplexity API"""
        
        if not self.api_key or self.api_key == "your_perplexity_api_key_here":
            return {
                "success": False,
                "error": "PERPLEXITY_API_KEY не установлен или установлен по умолчанию",
                "facts": []
            }
        
        # Простой и понятный промпт
        prompt = f"""Верни 3-5 исторических фактов о {object_type} "{name}" в {location} в формате JSON массива.
        Каждый факт должен иметь поля: "content", "year", "category".
        Пример: [{{"content": "Построен в XIX веке", "year": "1850", "category": "historical"}}]"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "sonar",
            "messages": [
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 800,
            "temperature": 0.3
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=20
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content'].strip()
                        
                        print(f"🔍 Perplexity response: {content[:100]}...")
                        
                        # Пытаемся распарсить JSON
                        try:
                            facts_data = json.loads(content)
                            if isinstance(facts_data, list):
                                return {
                                    "success": True,
                                    "facts": facts_data,
                                    "source": "perplexity"
                                }
                            else:
                                raise ValueError("Response is not a list")
                                
                        except (json.JSONDecodeError, ValueError):
                            # Создаём факты из текстового ответа
                            lines = [line.strip() for line in content.split('.') if len(line.strip()) > 20]
                            facts = []
                            for line in lines[:4]:
                                facts.append({
                                    "content": line,
                                    "year": None,
                                    "category": "historical" 
                                })
                            return {
                                "success": True,
                                "facts": facts,
                                "source": "perplexity_text"
                            }
                            
                    elif response.status == 401:
                        return {
                            "success": False,
                            "error": "Неверный API ключ Perplexity",
                            "facts": []
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"API error {response.status}: {error_text}",
                            "facts": []
                        }
                        
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Timeout - Perplexity API не отвечает",
                "facts": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Request error: {str(e)}",
                "facts": []
            }
    
    async def get_facts_for_object(self, object_data: Dict) -> Dict[str, Any]:
        """Получение фактов для конкретного объекта"""
        object_type_map = {
            "district": "район",
            "street": "улица", 
            "building": "дом"
        }
        
        object_type_ru = object_type_map.get(object_data['type'], object_data['type'])
        object_name = object_data.get('name', object_data.get('address', ''))
        
        print(f"🔍 Запрос фактов для {object_type_ru}: {object_name}")
        
        # Сначала пробуем Perplexity
        perplexity_result = await self.get_historical_facts(object_type_ru, object_name)
        
        if perplexity_result['success'] and perplexity_result['facts']:
            print(f"   ✅ Perplexity вернул {len(perplexity_result['facts'])} фактов")
            return perplexity_result
        else:
            print(f"   ⚠️  Perplexity не сработал: {perplexity_result.get('error', 'unknown error')}")
            
            # Используем локальные факты как резерв
            if object_data.get('facts'):
                local_facts = [{"content": fact, "year": None, "category": "local"} for fact in object_data['facts'][:4]]
                print(f"   🔄 Используем {len(local_facts)} локальных фактов")
                return {
                    "success": True,
                    "facts": local_facts,
                    "source": "local_fallback"
                }
            else:
                # Генерируем базовые факты
                basic_facts = self._generate_basic_facts(object_type_ru, object_name)
                print(f"   🔄 Используем {len(basic_facts)} базовых фактов")
                return {
                    "success": True,
                    "facts": basic_facts,
                    "source": "basic_fallback"
                }
    
    def _generate_basic_facts(self, object_type: str, object_name: str) -> List[Dict]:
        """Генерация базовых фактов когда нет других данных"""
        if object_type == "район":
            return [
                {"content": f"{object_name} - один из исторических районов Москвы", "year": None, "category": "historical"},
                {"content": "Имеет богатую архитектурную и культурную историю", "year": None, "category": "cultural"},
                {"content": "В районе сохранились памятники архитектуры разных эпох", "year": None, "category": "architectural"}
            ]
        elif object_type == "улица":
            return [
                {"content": f"{object_name} - одна из старых улиц Москвы", "year": None, "category": "historical"},
                {"content": "Улица сохранила историческую застройку и атмосферу", "year": None, "category": "architectural"},
                {"content": "Связана с именами известных москвичей и событиями", "year": None, "category": "personal"}
            ]
        else:  # building
            return [
                {"content": f"Здание по адресу {object_name} - памятник архитектуры", "year": None, "category": "architectural"},
                {"content": "Построено в историческом стиле характерном для Москвы", "year": None, "category": "historical"},
                {"content": "Является частью культурного наследия города", "year": None, "category": "cultural"}
            ]
