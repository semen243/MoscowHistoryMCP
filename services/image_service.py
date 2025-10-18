import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class ImageService:
    def __init__(self):
        self.styles = {
            "coat_of_arms": {
                "description": "Официальный герб района",
                "processing": "official",
                "requirements": "png/svg высокого качества"
            },
            "architectural_watercolor_sempe": {
                "description": "Архитектурная акварель в стиле Jean-Jacques Sempé",
                "processing": "ai_style_transfer", 
                "requirements": "мягкие линии, лёгкие тени, ручная текстура бумаги"
            }
        }
    
    def get_image_plan(self, object_type: str, object_data: Dict) -> Dict[str, Any]:
        """План обработки изображения для объекта"""
        
        style = "coat_of_arms" if object_type == "district" else "architectural_watercolor_sempe"
        style_info = self.styles[style]
        
        return {
            "object_type": object_type,
            "object_name": object_data.get('name', object_data.get('address', '')),
            "style": style,
            "style_description": style_info['description'],
            "processing": style_info['processing'],
            "requirements": style_info['requirements'],
            "output_format": "jpg",
            "min_resolution": "1200x800"
        }
    
    async def generate_image_prompt(self, object_data: Dict, object_type: str) -> str:
        """Генерация промпта для создания изображения"""
        
        if object_type == "district":
            return f"Официальный герб района {object_data.get('name', '')} Москвы, векторная графика, чистые линии"
        
        elif object_type == "street":
            return f"Улица {object_data.get('name', '')} в Москве, архитектурная акварель в стиле Jean-Jacques Sempé, мягкие линии, лёгкие тени, пастельные тона, текстура бумаги"
        
        else:  # building
            return f"Дом по адресу {object_data.get('address', '')} в Москве, архитектурная акварель в стиле Jean-Jacques Sempé, мягкие линии, лёгкие тени, старинная Москва"
    
    def validate_image_requirements(self, image_plan: Dict) -> Dict[str, Any]:
        """Валидация требований к изображению"""
        # Здесь будет реальная валидация, пока заглушка
        return {
            "valid": True,
            "checks": {
                "resolution": "≥1200px - OK",
                "format": "jpg/png - OK", 
                "style": f"{image_plan['style']} - OK",
                "watermark": "без водяных знаков - OK"
            }
        }
