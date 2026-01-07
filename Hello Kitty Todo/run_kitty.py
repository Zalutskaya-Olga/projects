import uvicorn
import os
import sys

print("🌸🎀 Hello Kitty Todo API 🎀🌸")

print("\nПроверка файлов:")
print(f"/app/app/main.py: {os.path.exists('/app/app/main.py')}")

try:
    sys.path.insert(0, '/app')

    from app.main import app_instance

    print("✅ Приложение импортировано успешно!")

    uvicorn.run(
        app=app_instance,
        host="0.0.0.0",
        port=8000,
        reload=False
    )
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback

    traceback.print_exc()
    exit(1)