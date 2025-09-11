import asyncio
import json
import sys
from pathlib import Path
from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from app.db.session import AsyncSessionLocal
from app.models.dialogs import Dictionary, Phrase


def get_dictionaries_folder_in1(custom_path: str | None = None) -> Path:
    if custom_path:
        return Path(custom_path).resolve()
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / "instruments" / "dictionaries" / "in1"


def parse_filename_for_dictionary(file_path: Path) -> tuple[str, str]:
    """Возвращает (description, title) из имени файла.
    Пример: "Возражения_objections.json" → ("Возражения", "objections").
    Если символ '_' отсутствует, description = "", title = stem.
    """
    stem = file_path.stem
    if "_" not in stem:
        return "", stem
    description, title = stem.split("_", 1)
    return description, title


async def get_or_create_dictionary(
    db: AsyncSession,
    *,
    title: str,
    description: str | None,
) -> Dictionary:
    result = await db.execute(select(Dictionary).where(Dictionary.title == title))
    dictionary: Dictionary | None = result.scalar_one_or_none()
    if dictionary:
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


async def load_existing_normal_forms(db: AsyncSession, dictionary_id) -> set[str]:
    result = await db.execute(
        select(Phrase.normal_form).where(Phrase.dictionary_id == dictionary_id)
    )
    return {row[0] for row in result.fetchall()}


def parse_json_file_in1(file_path: Path) -> List[Tuple[str, str]]:
    """Читает json формата {"phrase": "normal_form", ...}.
    Возвращает список пар (phrase, normal_form).
    Пропускает записи, где ключ/значение не строки.
    """
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return []

    pairs: List[Tuple[str, str]] = []
    for phrase, normal_form in data.items():
        if isinstance(phrase, str) and isinstance(normal_form, str):
            pairs.append((phrase, normal_form))
    return pairs


async def import_file(db: AsyncSession, file_path: Path) -> dict:
    description, title = parse_filename_for_dictionary(file_path)
    dictionary = await get_or_create_dictionary(db, title=title, description=description or None)

    pairs = parse_json_file_in1(file_path)
    if not pairs:
        return {"title": title, "description": description, "inserted": 0, "skipped": 0}

    to_insert: List[Phrase] = []
    skipped = 0
    for phrase, normal_form in pairs:
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

    return {
        "title": title,
        "description": description,
        "inserted": len(to_insert),
        "skipped": skipped,
    }


async def run_import(folder: Path) -> list[dict]:
    reports: list[dict] = []
    async with AsyncSessionLocal() as db:
        for file_path in sorted(folder.glob("*.json")):
            report = await import_file(db, file_path)
            reports.append(report)
    return reports


async def main() -> None:
    import sys

    folder = get_dictionaries_folder_in1(sys.argv[1] if len(sys.argv) > 1 else None)
    if not folder.exists() or not folder.is_dir():
        raise SystemExit(f"Папка со словарями не найдена: {folder}")

    reports = await run_import(folder)
    total_inserted = sum(r["inserted"] for r in reports)
    total_skipped = sum(r["skipped"] for r in reports)

    print(
        f"Импорт in1 завершён. Файлов: {len(reports)}, добавлено фраз: {total_inserted}, пропущено: {total_skipped}"
    )
    for r in reports:
        print(
            f" - {r['description']}_{r['title']}: +{r['inserted']} / skip {r['skipped']}"
        )


if __name__ == "__main__":
    asyncio.run(main())


