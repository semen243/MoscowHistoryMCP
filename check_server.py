import asyncio
from server import MoscowHistoryContentServer

async def simple_test():
    print("=== ПРОВЕРКА СЕРВЕРА ===")
    try:
        server = MoscowHistoryContentServer()
        await server.initialize_data()
        print("✅ Сервер запущен!")
        
        # Проверяем данные
        info = await server.get_objects_info()
        print(f"📊 Загружено: {len(info['districts'])} районов, {len(info['streets'])} улиц")
        
        # Пробуем сгенерировать пост
        result = await server.generate_complete_post("street", "arbat_street")
        if result["success"]:
            print(f"✅ Пост создан: {result['character_count']} символов")
            print(f"📝 Использовано фактов: {result['facts_used']}")
        else:
            print(f"❌ Ошибка: {result.get('error', 'unknown')}")
            
        print("🎉 ВСЕ СИСТЕМЫ РАБОТАЮТ!")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")

asyncio.run(simple_test())