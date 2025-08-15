import asyncio
import json
from pathlib import Path
from typing import Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.dialogs import Dictionary, Phrase


# Таблица переводов названий словарей
TITLE_TRANSLATIONS: Dict[str, str] = {
    "Concern": "БеспокойСтво",
    "Rudeness": "Грубости",
    "Apologies": "Извинения",
    "Conflict": "Конфликт",
    "Conflict2": "Конфликт2",
    "Conflict3": "Конфликт3",
    "Not": "Не",
    "Negative": "Негатив",
    "Unwanted": "Нежелательные",
    "Obscene": "Нецензурные",
    "Expectations": "Ожидания",
    "Justifiable": "Оправдательные",
    "Insults": "Оскорбления",
    "Refusals": "Отказы",
    "Refusals2": "Отказы2",
    "Blurriness": "Размытость",
    "Slang": "Сленг",
    "Diminutives": "Уменьшительные",
}

# Регистронезависимое отображение
_TITLE_TRANSLATIONS_LOWER: Dict[str, str] = {k.lower(): v for k, v in TITLE_TRANSLATIONS.items()}


def get_dictionaries_folder(custom_path: str | None = None) -> Path:
    if custom_path:
        return Path(custom_path).resolve()
    # Проектный путь: <repo_root>/instruments/dictionaries/in
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "instruments" / "dictionaries" / "in"


async def get_or_create_dictionary(
    db: AsyncSession,
    title: str,
    description: str | None,
) -> Dictionary:
    result = await db.execute(select(Dictionary).where(Dictionary.title == title))
    dictionary: Dictionary | None = result.scalar_one_or_none()
    if dictionary:
        # обновим описание при необходимости
        if description and dictionary.description != description:
            dictionary.description = description
            db.add(dictionary)
            await db.commit()
            await db.refresh(dictionary)
        return dictionary

    dictionary = Dictionary(title=title, description=description)
    db.add(dictionary)
    await db.commit()
    await db.refresh(dictionary)
    return dictionary


async def load_existing_normal_forms(
    db: AsyncSession,
    dictionary_id,
) -> set[str]:
    result = await db.execute(
        select(Phrase.normal_form).where(Phrase.dictionary_id == dictionary_id)
    )
    return {row[0] for row in result.fetchall()}


def parse_json_file(file_path: Path) -> List[Tuple[str, str]]:
    """Возвращает список пар (normal_form, phrase). Берём нулевой элемент списка в значении.
    Пропускаем записи, где значение не список или список пустой.
    """
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return []

    pairs: List[Tuple[str, str]] = []
    for normal_form, value in data.items():
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, str) and isinstance(normal_form, str):
                pairs.append((normal_form, first))
    return pairs


async def import_file(db: AsyncSession, file_path: Path) -> dict:
    title = file_path.stem  # имя файла без расширения
    # поддержка различий регистра между ОС
    description = TITLE_TRANSLATIONS.get(title) or _TITLE_TRANSLATIONS_LOWER.get(title.lower())

    dictionary = await get_or_create_dictionary(db, title=title, description=description)

    pairs = parse_json_file(file_path)
    if not pairs:
        return {"title": title, "inserted": 0, "skipped": 0}

    existing = await load_existing_normal_forms(db, dictionary.id)

    to_insert: List[Phrase] = []
    skipped = 0
    for normal_form, phrase in pairs:
        if normal_form in existing:
            skipped += 1
            continue
        to_insert.append(
            Phrase(
                dictionary_id=dictionary.id,
                normal_form=normal_form,
                phrase=phrase,
            )
        )

    if to_insert:
        db.add_all(to_insert)
        await db.commit()

    return {"title": title, "inserted": len(to_insert), "skipped": skipped}


async def run_import(folder: Path) -> List[dict]:
    reports: List[dict] = []
    async with AsyncSessionLocal() as db:
        for file_path in sorted(folder.glob("*.json")):
            report = await import_file(db, file_path)
            reports.append(report)
    return reports


async def main() -> None:
    # Можно передать путь к папке первым аргументом командной строки
    import sys

    folder = get_dictionaries_folder(sys.argv[1] if len(sys.argv) > 1 else None)
    if not folder.exists() or not folder.is_dir():
        raise SystemExit(f"Папка с словарями не найдена: {folder}")

    reports = await run_import(folder)
    total_inserted = sum(r["inserted"] for r in reports)
    total_skipped = sum(r["skipped"] for r in reports)

    print(f"Импорт завершён. Файлов: {len(reports)}, добавлено фраз: {total_inserted}, пропущено: {total_skipped}")
    for r in reports:
        print(f" - {r['title']}: +{r['inserted']} / skip {r['skipped']}")


if __name__ == "__main__":
    asyncio.run(main())


