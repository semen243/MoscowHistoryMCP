from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
import codecs

class District(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    coat_of_arms_url: Optional[str] = None
    published: bool = False
    last_published: Optional[datetime] = None
    interesting_facts: List[str] = []

    @classmethod
    def load_all(cls) -> List['District']:
        """Загрузка всех районов из JSON"""
        try:
            with open('data/moscow_objects.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [cls(**district_data) for district_data in data['districts']]
        except FileNotFoundError:
            print("❌ Файл data/moscow_objects.json не найден")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка чтения JSON: {e}")
            # Пробуем прочитать с обработкой BOM
            try:
                with open('data/moscow_objects.json', 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    return [cls(**district_data) for district_data in data['districts']]
            except Exception as e2:
                print(f"❌ Ошибка при повторной попытке: {e2}")
                return []

class Street(BaseModel):
    id: str
    name: str
    district_id: str
    interesting_facts: List[str] = []
    published: bool = False
    last_published: Optional[datetime] = None

    @classmethod
    def load_all(cls) -> List['Street']:
        """Загрузка всех улиц из JSON"""
        try:
            with open('data/moscow_objects.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [cls(**street_data) for street_data in data['streets']]
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            # Пробуем прочитать с обработкой BOM
            try:
                with open('data/moscow_objects.json', 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    return [cls(**street_data) for street_data in data['streets']]
            except:
                return []

class Building(BaseModel):
    id: str
    address: str
    street_id: str
    district_id: str
    interesting_facts: List[str] = []
    published: bool = False
    last_published: Optional[datetime] = None
    architectural_style: Optional[str] = None

    @classmethod
    def load_all(cls) -> List['Building']:
        """Загрузка всех домов из JSON"""
        try:
            with open('data/moscow_objects.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [cls(**building_data) for building_data in data['buildings']]
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            # Пробуем прочитать с обработкой BOM
            try:
                with open('data/moscow_objects.json', 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    return [cls(**building_data) for building_data in data['buildings']]
            except:
                return []

class Fact(BaseModel):
    content: str
    year: Optional[str] = None
    source: Optional[str] = None
    category: str  # historical, architectural, personal, legend

class Post(BaseModel):
    id: str
    object_type: str  # district, street, building
    object_name: str
    text: str
    image_path: str
    publish_time: str
    character_count: int
