"""PySide6 UI for the Verse Wallpaper app."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from PIL.ImageQt import ImageQt

from .constants import BOOKS
from .cursor import advance_if_needed
from .db import BibleDB, available_databases, book_name
from .parser import parse_reference
from .renderer import AnalyticsContent, ScriptureContent, WallpaperRenderer
from .state import AppState, StateStore
from .wallpaper import save_wallpaper, set_wallpaper


@dataclass
class TranslationOption:
    id: str
    name: str
    path: Path


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, state_store: StateStore) -> None:
        super().__init__()
        self.state_store = state_store
        self.state = self.state_store.load()
        self.renderer = WallpaperRenderer()
        self.bible: BibleDB | None = None
        self.translations: list[TranslationOption] = []
        self.setWindowTitle("Verse Wallpaper")
        self.resize(900, 600)
        self._build_ui()
        self._load_translations()
        self._apply_state()

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        form_layout = QtWidgets.QFormLayout()
        self.translation_combo = QtWidgets.QComboBox()
        self.translation_combo.currentIndexChanged.connect(self._on_translation_changed)
        form_layout.addRow("Translation", self.translation_combo)

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["Chapter Daily", "Verse Daily"])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        form_layout.addRow("Mode", self.mode_combo)

        self.testament_combo = QtWidgets.QComboBox()
        self.testament_combo.addItems(["All", "Old Testament", "New Testament"])
        self.testament_combo.currentIndexChanged.connect(self._on_testament_changed)
        form_layout.addRow("Testament", self.testament_combo)

        self.book_combo = QtWidgets.QComboBox()
        self.book_combo.currentIndexChanged.connect(self._on_book_changed)
        form_layout.addRow("Book", self.book_combo)

        self.chapter_combo = QtWidgets.QComboBox()
        self.chapter_combo.currentIndexChanged.connect(self._on_chapter_changed)
        form_layout.addRow("Chapter", self.chapter_combo)

        self.verse_combo = QtWidgets.QComboBox()
        self.verse_combo.currentIndexChanged.connect(self._on_verse_changed)
        form_layout.addRow("Verse", self.verse_combo)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Search (e.g., Rom 1:2)")
        self.search_input.returnPressed.connect(self._on_search)
        form_layout.addRow("Search", self.search_input)

        layout.addLayout(form_layout)

        button_layout = QtWidgets.QHBoxLayout()
        self.apply_button = QtWidgets.QPushButton("Apply")
        self.apply_button.clicked.connect(self._on_apply)
        self.preview_button = QtWidgets.QPushButton("Preview")
        self.preview_button.clicked.connect(self._on_preview)
        self.set_now_button = QtWidgets.QPushButton("Set Now")
        self.set_now_button.clicked.connect(self._on_set_now)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.set_now_button)
        layout.addLayout(button_layout)

        self.preview_label = QtWidgets.QLabel()
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid #ccc;")
        layout.addWidget(self.preview_label, stretch=1)

        self.setCentralWidget(central)

    def _load_translations(self) -> None:
        search_root = Path(self.state.db_path).parent if self.state.db_path else Path.cwd() / "truth"
        db_paths = available_databases(search_root) if search_root.exists() else []
        translations: list[TranslationOption] = []
        for path in db_paths:
            try:
                bible = BibleDB(path)
                translation = bible.list_translations()[0]
                translations.append(TranslationOption(id=str(path), name=translation.name, path=path))
                bible.close()
            except Exception:
                continue
        if not translations:
            self._prompt_for_db()
            return
        self.translations = translations
        self.translation_combo.blockSignals(True)
        self.translation_combo.clear()
        for translation in translations:
            self.translation_combo.addItem(translation.name, translation.id)
        self.translation_combo.blockSignals(False)

    def _prompt_for_db(self) -> None:
        QtWidgets.QMessageBox.warning(
            self,
            "Bible Database Missing",
            "No Bible SQLite database found. Please locate a SQLite export.",
        )
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Bible SQLite", str(Path.cwd()), "SQLite (*.sqlite *.db)"
        )
        if not file_path:
            return
        path = Path(file_path)
        try:
            bible = BibleDB(path)
            translation = bible.list_translations()[0]
            bible.close()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Invalid Database", str(exc))
            return
        self.translations = [TranslationOption(id=str(path), name=translation.name, path=path)]
        self.translation_combo.clear()
        self.translation_combo.addItem(translation.name, str(path))
        self.translation_combo.setCurrentIndex(0)
        self.state.db_path = str(path)
        self._open_bible(path)

    def _open_bible(self, path: Path) -> None:
        if self.bible:
            self.bible.close()
        self.bible = BibleDB(path)
        self.state.db_path = str(path)

    def _apply_state(self) -> None:
        if self.translations:
            selected = None
            for index, translation in enumerate(self.translations):
                if translation.id == self.state.translation_id or translation.id == self.state.db_path:
                    selected = index
                    break
            if selected is None:
                selected = 0
            self.translation_combo.setCurrentIndex(selected)
            self._open_bible(self.translations[selected].path)
            self.state.translation_id = self.translations[selected].id
        if not self.bible:
            return
        self.state = advance_if_needed(self.state, self.bible)
        self.state_store.save(self.state)

        if self.state.mode == "chapter":
            self.mode_combo.setCurrentIndex(0)
        else:
            self.mode_combo.setCurrentIndex(1)
        if self.state.testament_filter == "ot":
            self.testament_combo.setCurrentIndex(1)
        elif self.state.testament_filter == "nt":
            self.testament_combo.setCurrentIndex(2)
        else:
            self.testament_combo.setCurrentIndex(0)
        self._populate_books()
        self._select_book(self.state.selected_book)
        self._populate_chapters(self.state.selected_book)
        self._select_chapter(self.state.selected_chapter)
        self._populate_verses(self.state.selected_book, self.state.selected_chapter)
        self._select_verse(self.state.selected_verse)
        self._update_verse_enabled()

    def _on_translation_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.translations):
            return
        translation = self.translations[index]
        self._open_bible(translation.path)
        self.state.translation_id = translation.id
        self.state_store.save(self.state)
        self._populate_books()
        if self.book_combo.count() > 0:
            self.book_combo.setCurrentIndex(0)

    def _on_mode_changed(self) -> None:
        self.state.mode = "chapter" if self.mode_combo.currentIndex() == 0 else "verse"
        self._update_verse_enabled()
        self.state_store.save(self.state)

    def _on_testament_changed(self) -> None:
        index = self.testament_combo.currentIndex()
        if index == 1:
            self.state.testament_filter = "ot"
        elif index == 2:
            self.state.testament_filter = "nt"
        else:
            self.state.testament_filter = "all"
        self._populate_books()
        if self.book_combo.count() > 0:
            self.book_combo.setCurrentIndex(0)

    def _update_verse_enabled(self) -> None:
        self.verse_combo.setEnabled(self.state.mode == "verse")

    def _populate_books(self) -> None:
        self.book_combo.blockSignals(True)
        self.book_combo.clear()
        for book in BOOKS:
            if self.state.testament_filter == "ot" and book.testament != "OT":
                continue
            if self.state.testament_filter == "nt" and book.testament != "NT":
                continue
            self.book_combo.addItem(book.name, book.number)
        self.book_combo.blockSignals(False)

    def _populate_chapters(self, book_number: int) -> None:
        if not self.bible:
            return
        chapters = self.bible.chapters_for_book(book_number)
        self.chapter_combo.blockSignals(True)
        self.chapter_combo.clear()
        for chapter in chapters:
            self.chapter_combo.addItem(str(chapter), chapter)
        self.chapter_combo.blockSignals(False)

    def _populate_verses(self, book_number: int, chapter: int) -> None:
        if not self.bible:
            return
        verses = self.bible.verses_for_chapter(book_number, chapter)
        self.verse_combo.blockSignals(True)
        self.verse_combo.clear()
        for verse in verses:
            self.verse_combo.addItem(str(verse), verse)
        self.verse_combo.blockSignals(False)

    def _on_book_changed(self) -> None:
        book_number = self.book_combo.currentData()
        if not book_number:
            return
        self.state.selected_book = int(book_number)
        self._populate_chapters(int(book_number))
        if self.chapter_combo.count() > 0:
            self.chapter_combo.setCurrentIndex(0)
        self.state_store.save(self.state)

    def _on_chapter_changed(self) -> None:
        chapter = self.chapter_combo.currentData()
        book = self.book_combo.currentData()
        if not chapter or not book:
            return
        self.state.selected_chapter = int(chapter)
        self._populate_verses(int(book), int(chapter))
        if self.verse_combo.count() > 0:
            self.verse_combo.setCurrentIndex(0)
        self.state_store.save(self.state)

    def _on_verse_changed(self) -> None:
        verse = self.verse_combo.currentData()
        if not verse:
            return
        self.state.selected_verse = int(verse)
        self.state_store.save(self.state)

    def _select_book(self, book_number: int) -> None:
        index = self.book_combo.findData(book_number)
        if index >= 0:
            self.book_combo.blockSignals(True)
            self.book_combo.setCurrentIndex(index)
            self.book_combo.blockSignals(False)

    def _select_chapter(self, chapter: int) -> None:
        index = self.chapter_combo.findData(chapter)
        if index >= 0:
            self.chapter_combo.blockSignals(True)
            self.chapter_combo.setCurrentIndex(index)
            self.chapter_combo.blockSignals(False)

    def _select_verse(self, verse: int) -> None:
        index = self.verse_combo.findData(verse)
        if index >= 0:
            self.verse_combo.blockSignals(True)
            self.verse_combo.setCurrentIndex(index)
            self.verse_combo.blockSignals(False)

    def _on_search(self) -> None:
        text = self.search_input.text().strip()
        if not text:
            return
        parsed = parse_reference(text)
        if not parsed:
            QtWidgets.QMessageBox.warning(self, "Invalid Reference", "Could not parse reference.")
            return
        self._select_book(parsed.book_number)
        self._populate_chapters(parsed.book_number)
        chapter_index = self.chapter_combo.findData(parsed.chapter)
        if chapter_index < 0:
            QtWidgets.QMessageBox.warning(self, "Invalid Reference", "Chapter not found.")
            return
        self.chapter_combo.setCurrentIndex(chapter_index)
        self._populate_verses(parsed.book_number, parsed.chapter)
        if parsed.verse:
            verse_index = self.verse_combo.findData(parsed.verse)
            if verse_index < 0:
                QtWidgets.QMessageBox.warning(self, "Invalid Reference", "Verse not found.")
                return
            self.verse_combo.setCurrentIndex(verse_index)
        self.state.selected_book = parsed.book_number
        self.state.selected_chapter = parsed.chapter
        if parsed.verse:
            self.state.selected_verse = parsed.verse
        self.state_store.save(self.state)

    def _on_apply(self) -> None:
        if not self.bible:
            self._prompt_for_db()
            return
        self.state.mode = "chapter" if self.mode_combo.currentIndex() == 0 else "verse"
        self.state.cursor.book = int(self.book_combo.currentData())
        self.state.cursor.chapter = int(self.chapter_combo.currentData())
        self.state.cursor.verse = int(self.verse_combo.currentData() or 1)
        self.state.selected_book = self.state.cursor.book
        self.state.selected_chapter = self.state.cursor.chapter
        self.state.selected_verse = self.state.cursor.verse
        self.state_store.save(self.state)
        self._render_and_set()

    def _on_preview(self) -> None:
        if not self.bible:
            self._prompt_for_db()
            return
        image = self._render(cursor_override=self._selection_cursor())
        qt_image = ImageQt(image)
        pixmap = QtGui.QPixmap.fromImage(qt_image)
        scaled = pixmap.scaled(
            self.preview_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)

    def _on_set_now(self) -> None:
        if not self.bible:
            self._prompt_for_db()
            return
        self._render_and_set()

    def _selection_cursor(self):
        return type(self.state.cursor)(
            book=int(self.book_combo.currentData()),
            chapter=int(self.chapter_combo.currentData()),
            verse=int(self.verse_combo.currentData() or 1),
        )

    def _render(self, cursor_override=None):
        if not self.bible:
            raise RuntimeError("Bible database not loaded.")
        translation_name = self.translation_combo.currentText()
        cursor = cursor_override or self.state.cursor
        book = cursor.book
        chapter = cursor.chapter
        verse = cursor.verse
        if self.state.mode == "chapter":
            verses = self.bible.chapter_text(book, chapter)
            lines = [f"{num} {text}" for num, text in verses]
            header = f"{book_name(book)} {chapter}"
            is_chapter = True
        else:
            text = self.bible.verse_text(book, chapter, verse)
            lines = [text]
            header = f"{book_name(book)} {chapter}:{verse}"
            is_chapter = False
        scripture = ScriptureContent(
            header=header,
            translation=translation_name,
            lines=lines,
            is_chapter=is_chapter,
        )
        book_lengths = self.bible.book_lengths()
        total_verses = sum(length for _, length in book_lengths)
        verse_index = self.bible.verse_index(book, chapter, verse)
        progress_percent = (verse_index / total_verses * 100) if total_verses else 0.0
        days_advanced = verse_index if self.state.mode == "verse" else chapter
        analytics = AnalyticsContent(
            book_lengths=book_lengths,
            current_book=book,
            current_chapter=chapter,
            current_verse=verse,
            progress_percent=progress_percent,
            days_advanced=days_advanced,
        )
        return self.renderer.render(scripture, analytics)

    def _render_and_set(self) -> None:
        image = self._render()
        path = save_wallpaper(image)
        set_wallpaper(path)


class VerseWallpaperApp(QtWidgets.QApplication):
    def __init__(self, state_store: StateStore) -> None:
        super().__init__()
        self.main_window = MainWindow(state_store)
        self.main_window.show()
