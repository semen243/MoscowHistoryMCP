import asyncio
import random
from datetime import datetime, time, timedelta
from typing import List, Dict, Any
import yaml
import os
from dotenv import load_dotenv

# Импорты из mcp
from mcp import ClientSession, StdioServerParameters, stdio_server, Tool
from mcp.server import Server
from mcp.types import Tool as ToolType

from models.district import District, Street, Building, Fact, Post
from services.perplexity_service import PerplexityService
from services.gpt_service import GPTService
from services.image_service import ImageService

# Загружаем переменные окружения
load_dotenv()

class MoscowHistoryContentServer:
    def __init__(self):
        self.server = Server("moscow-history-pipeline")
        self.districts: List[District] = []
        self.streets: List[Street] = []
        self.buildings: List[Building] = []
        self.published_posts: set = set()
        self.perplexity = PerplexityService()
        self.gpt = GPTService()
        self.images = ImageService()
        self.load_config()
        
    def load_config(self):
        """Загрузка конфигурации"""
        with open('config/mcp_config.yaml', 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        print("✅ Конфигурация загружена")
    
    async def initialize_data(self):
        """Инициализация начальных данных"""
        self.districts = District.load_all()
        self.streets = Street.load_all() 
        self.buildings = Building.load_all()
        
        print(f"✅ Данные загружены:")
        print(f"   • Районов: {len(self.districts)}")
        print(f"   • Улиц: {len(self.streets)}")
        print(f"   • Дома: {len(self.buildings)}")
        
        # Проверяем доступность API
        self._check_apis()
    
    def _check_apis(self):
        """Проверка доступности API"""
        apis = {
            "Perplexity": bool(os.getenv('PERPLEXITY_API_KEY')) and os.getenv('PERPLEXITY_API_KEY') != "your_perplexity_api_key_here",
            "OpenAI GPT": bool(os.getenv('OPENAI_API_KEY')) and os.getenv('OPENAI_API_KEY') != "your_openai_api_key_here"
        }
        
        print("🔍 Проверка API:")
        for api_name, available in apis.items():
            status = "✅ настроен" if available else "⚠️  не настроен (используем резервные варианты)"
            print(f"   • {api_name}: {status}")
    
    def register_tools(self):
        """Регистрация инструментов MCP"""
        
        @self.server.list_tools()
        async def list_tools():
            return [
                ToolType(
                    name="generate_daily_schedule",
                    description="Генерация расписания на день (24 поста)",
                    inputSchema={"type": "object", "properties": {}}
                ),
                ToolType(
                    name="get_server_info", 
                    description="Получение информации о сервере",
                    inputSchema={"type": "object", "properties": {}}
                ),
                ToolType(
                    name="get_objects_info",
                    description="Получение информации об объектах Москвы", 
                    inputSchema={"type": "object", "properties": {}}
                ),
                ToolType(
                    name="generate_daily_content",
                    description="Генерация контента на день",
                    inputSchema={"type": "object", "properties": {}}
                ),
                ToolType(
                    name="get_facts_for_object",
                    description="Получение фактов для объекта через Perplexity",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "object_type": {"type": "string", "enum": ["district", "street", "building"]},
                            "object_name": {"type": "string"}
                        },
                        "required": ["object_type", "object_name"]
                    }
                ),
                ToolType(
                    name="generate_complete_post",
                    description="Генерация полного поста (факты + текст + изображение)",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "object_type": {"type": "string", "enum": ["district", "street", "building"]},
                            "object_id": {"type": "string"}
                        },
                        "required": ["object_type", "object_id"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict) -> Dict[str, Any]:
            if name == "generate_daily_schedule":
                return await self._generate_schedule()
            elif name == "get_server_info":
                return await self.get_server_info()
            elif name == "get_objects_info":
                return await self.get_objects_info()
            elif name == "generate_daily_content":
                return await self.generate_daily_content()
            elif name == "get_facts_for_object":
                return await self.perplexity.get_historical_facts(
                    arguments["object_type"],
                    arguments["object_name"]
                )
            elif name == "generate_complete_post":
                return await self.generate_complete_post(
                    arguments["object_type"],
                    arguments["object_id"]
                )
            else:
                raise ValueError(f"Unknown tool: {name}")
        
        print("✅ Инструменты MCP зарегистрированы")

    async def get_server_info(self) -> Dict[str, Any]:
        """Получение информации о сервере"""
        return {
            "name": self.config['server']['name'],
            "version": self.config['server']['version'],
            "description": self.config['server']['description'],
            "status": "running",
            "apis_available": {
                "perplexity": bool(os.getenv('PERPLEXITY_API_KEY')) and os.getenv('PERPLEXITY_API_KEY') != "your_perplexity_api_key_here",
                "openai_gpt": bool(os.getenv('OPENAI_API_KEY')) and os.getenv('OPENAI_API_KEY') != "your_openai_api_key_here"
            },
            "objects_loaded": {
                "districts": len(self.districts),
                "streets": len(self.streets), 
                "buildings": len(self.buildings)
            }
        }

    async def get_objects_info(self) -> Dict[str, Any]:
        """Получение информации об объектах"""
        return {
            "districts": [{"id": d.id, "name": d.name} for d in self.districts],
            "streets": [{"id": s.id, "name": s.name, "district": s.district_id} for s in self.streets],
            "buildings": [{"id": b.id, "address": b.address, "street": b.street_id} for b in self.buildings]
        }

    async def _generate_schedule(self) -> Dict[str, Any]:
        """Генерация 24 случайных времен публикации"""
        times = []
        start_time_str = self.config['content']['operating_hours']['start']
        end_time_str = self.config['content']['operating_hours']['end']
        
        start_hour, start_minute = map(int, start_time_str.split(':'))
        end_hour, end_minute = map(int, end_time_str.split(':'))
        
        current_time = time(start_hour, start_minute)
        
        for i in range(24):
            min_interval = self.config['content']['min_interval_minutes']
            max_interval = self.config['content']['max_interval_minutes']
            minutes = random.randint(min_interval, max_interval)
            
            total_minutes = current_time.hour * 60 + current_time.minute + minutes
            new_hour = total_minutes // 60
            new_minute = total_minutes % 60
            
            if new_hour > end_hour or (new_hour == end_hour and new_minute > end_minute):
                break
                
            post_time = time(new_hour, new_minute)
            times.append(post_time.strftime("%H:%M"))
            current_time = post_time
        
        return {
            "schedule": times, 
            "total_posts": len(times),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "start_time": start_time_str,
            "end_time": end_time_str
        }

    async def generate_daily_content(self) -> Dict[str, Any]:
        """Генерация контента на день"""
        schedule = await self._generate_schedule()
        
        # Выбираем объекты для публикации
        selected_objects = []
        
        # 1 пост - район
        if self.districts:
            district = random.choice(self.districts)
            selected_objects.append({
                "type": "district",
                "id": district.id,
                "name": district.name,
                "description": district.description,
                "facts": district.interesting_facts
            })
        
        # Остальные посты - улицы и дома
        remaining_slots = schedule['total_posts'] - 1
        
        for i in range(remaining_slots):
            if random.random() < 0.7 and self.streets:  # 70% улицы
                street = random.choice(self.streets)
                selected_objects.append({
                    "type": "street", 
                    "id": street.id,
                    "name": street.name,
                    "district": street.district_id,
                    "facts": street.interesting_facts
                })
            elif self.buildings:  # 30% дома
                building = random.choice(self.buildings)
                selected_objects.append({
                    "type": "building",
                    "id": building.id, 
                    "address": building.address,
                    "architectural_style": building.architectural_style,
                    "facts": building.interesting_facts
                })
        
        return {
            "date": schedule['date'],
            "total_posts": len(selected_objects),
            "schedule": schedule['schedule'],
            "content_plan": [
                {
                    "time": schedule['schedule'][i] if i < len(schedule['schedule']) else "09:00",
                    "object": obj
                }
                for i, obj in enumerate(selected_objects)
            ]
        }

    async def generate_complete_post(self, object_type: str, object_id: str) -> Dict[str, Any]:
        """Генерация полного поста с фактами, текстом и изображением"""
        
        # Находим объект
        object_data = await self._find_object(object_type, object_id)
        if not object_data:
            return {"success": False, "error": f"Объект {object_type}/{object_id} не найден"}
        
        print(f"🎯 Генерация поста для {object_type}: {object_data.get('name', object_data.get('address', ''))}")
        
        # Получаем факты
        facts_result = await self.perplexity.get_facts_for_object(object_data)
        facts = facts_result.get('facts', [])
        source = facts_result.get('source', 'unknown')
        
        print(f"   📊 Использовано фактов: {len(facts)} (источник: {source})")
        
        # Генерируем текст
        post_result = await self.gpt.generate_complete_post(object_data, facts)
        
        # План изображения
        image_plan = self.images.get_image_plan(object_type, object_data)
        
        return {
            "success": True,
            "object": object_data,
            "post": post_result,
            "image": image_plan,
            "facts_used": len(facts),
            "facts_source": source,
            "character_count": post_result['character_count'],
            "ready_for_publication": post_result['character_count'] >= 600,
            "generation_model": post_result.get('generation_model', 'unknown')
        }

    async def _find_object(self, object_type: str, object_id: str) -> Dict[str, Any]:
        """Поиск объекта по типу и ID"""
        if object_type == "district":
            for district in self.districts:
                if district.id == object_id:
                    return {
                        "type": "district", 
                        "id": district.id, 
                        "name": district.name, 
                        "description": district.description,
                        "facts": district.interesting_facts
                    }
        
        elif object_type == "street":
            for street in self.streets:
                if street.id == object_id:
                    return {
                        "type": "street", 
                        "id": street.id, 
                        "name": street.name, 
                        "district": street.district_id,
                        "facts": street.interesting_facts
                    }
        
        elif object_type == "building":
            for building in self.buildings:
                if building.id == object_id:
                    return {
                        "type": "building", 
                        "id": building.id, 
                        "address": building.address, 
                        "architectural_style": building.architectural_style,
                        "facts": building.interesting_facts
                    }
        
        return None

    async def run_demo(self):
        """Запуск в демо-режиме"""
        await self.initialize_data()
        
        server_info = await self.get_server_info()
        print("🚀 Moscow History Content Server")
        print(f"📝 Имя: {server_info['name']}")
        print(f"🔢 Версия: {server_info['version']}")
        print(f"📊 Загружено объектов: {server_info['objects_loaded']}")
        
        # Демонстрация работы
        print("\n" + "="*50)
        print("🎯 ДЕМОНСТРАЦИЯ РАБОТЫ СЕРВЕРА")
        print("="*50)
        
        # Демонстрация генерации полного поста
        print(f"\n🔧 ДЕМО: Генерация полного поста для улицы Арбат")
        
        post_result = await self.generate_complete_post("street", "arbat_street")
        
        if post_result['success']:
            print(f"   ✅ Пост сгенерирован успешно!")
            print(f"   📍 Объект: {post_result['object']['name']}")
            print(f"   📝 Символов: {post_result['character_count']}")
            print(f"   🤖 Модель: {post_result['generation_model']}")
            print(f"   🖼️ Стиль изображения: {post_result['image']['style_description']}")
            print(f"   📊 Фактов использовано: {post_result['facts_used']} (источник: {post_result['facts_source']})")
            print(f"   🚀 Готов к публикации: {'✅' if post_result['ready_for_publication'] else '❌'}")
            
            # Показываем часть текста
            text_preview = post_result['post']['text'][:200] + "..." if len(post_result['post']['text']) > 200 else post_result['post']['text']
            print(f"   📄 Текст: {text_preview}")
        else:
            print(f"   ❌ Ошибка генерации: {post_result.get('error', 'unknown')}")
        
        print(f"\n✅ СЕРВЕР ГОТОВ К РАБОТЕ!")
        print("💡 Сервер работает даже без API ключей - использует резервные варианты")

async def main():
    """Основная функция"""
    server = MoscowHistoryContentServer()
    await server.run_demo()

if __name__ == "__main__":
    asyncio.run(main())
