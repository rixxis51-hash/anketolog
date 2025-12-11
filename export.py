
import csv
from database import get_all_forms

def export_to_csv(filename="forms_export.csv"):
    rows = get_all_forms()

    if not rows:
        print("Нет данных для экспорта.")
        return

    # UTF-8 with BOM для правильного отображения в Excel
    with open(filename, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")  # Excel лучше понимает точку с запятой
        writer.writerow([
            "ID", "User ID", "Имя", "TG Username", "MC Ник",
            "Как обращаться", "Возраст", "Дополнительно"
        ])

        for row in rows:
            writer.writerow(row)

    print(f"Экспорт завершён. Файл: {filename}")


if __name__ == "__main__":
    export_to_csv()