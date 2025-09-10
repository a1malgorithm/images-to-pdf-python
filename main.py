import os
import re
import sys
from io import BytesIO
from typing import List, Iterable

from PIL import Image
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
    QLabel,
    QAbstractItemView,
    QGroupBox,
    QFormLayout,
    QSpinBox,
    QCheckBox,
    QProgressBar,
    QStyleFactory,
)


def natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


class ConvertWorker(QObject):
    progress = pyqtSignal(int, int, str)  # current, total, filename
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    canceled = pyqtSignal()

    def __init__(self, paths: List[str], save_path: str, max_w: int, max_h: int, dpi: int):
        super().__init__()
        self.paths = paths
        self.save_path = save_path
        self.max_w = max_w
        self.max_h = max_h
        self.dpi = dpi
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _fit_within(self, img: Image.Image) -> Image.Image:
        if self.max_w <= 0 and self.max_h <= 0:
            return img
        w, h = img.size
        max_w = self.max_w if self.max_w > 0 else w
        max_h = self.max_h if self.max_h > 0 else h
        scale = min(max_w / w, max_h / h)
        if scale >= 1:
            return img
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        return img.resize(new_size, Image.LANCZOS)

    def run(self):
        try:
            images: List[Image.Image] = []
            total = len(self.paths)
            for i, p in enumerate(self.paths, start=1):
                if self._cancel:
                    self.canceled.emit()
                    return
                try:
                    img = Image.open(p)
                    if img.mode in ("RGBA", "LA"):
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == "LA":
                            alpha = img.getchannel("A")
                            img = img.convert("RGBA")
                        else:
                            alpha = img.split()[-1]
                        bg.paste(img, mask=alpha)
                        img = bg
                    else:
                        img = img.convert("RGB")

                    img = self._fit_within(img)
                    images.append(img)
                finally:
                    self.progress.emit(i, total, os.path.basename(p))

            if not images:
                self.error.emit("No images to convert.")
                return

            # Note: PIL's PDF saver uses 'resolution' as DPI for size mapping.
            images[0].save(
                self.save_path,
                save_all=True,
                append_images=images[1:],
                resolution=float(self.dpi or 72),
            )
            self.finished.emit(self.save_path)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            for im in locals().get("images", []):
                try:
                    im.close()
                except Exception:
                    pass


class ImageListWidget(QListWidget):
    def __init__(self, add_paths_callback, allowed_exts: Iterable[str], parent=None):
        super().__init__(parent)
        self._add_paths = add_paths_callback
        self._exts = set(e.lower() for e in allowed_exts)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.source() is self:
            # Internal move
            super().dropEvent(event)
            return
        md = event.mimeData()
        if md.hasUrls():
            paths = []
            for u in md.urls():
                if u.isLocalFile():
                    paths.append(u.toLocalFile())
            if paths:
                self._add_paths(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image2PDF GUI — Image to PDF Converter")

        self.allowed_exts = {".jpg", ".jpeg", ".png", ".jfif"}

        self._build_ui()
        self.resize(900, 560)

    def _build_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Header with blue gradient
        header = QWidget(objectName="Header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        title = QLabel("Image2PDF GUI")
        subtitle = QLabel("Convert a folder or files to a single PDF")
        title.setStyleSheet("font-size: 20px; font-weight: 600; color: white;")
        subtitle.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.9);")
        title_box = QVBoxLayout()
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box, 1)
        root.addWidget(header)

        # Path row
        path_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Drop images or browse to add…")
        self.path_edit.setReadOnly(True)
        btn_browse_folder = QPushButton("Add Folder…")
        btn_browse_folder.clicked.connect(self.add_folder)
        btn_browse_files = QPushButton("Add Files…")
        btn_browse_files.clicked.connect(self.add_files)
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(btn_browse_folder)
        path_row.addWidget(btn_browse_files)
        root.addLayout(path_row)

        # List + controls
        self.list_widget = ImageListWidget(self._add_paths, self.allowed_exts)
        root.addWidget(self.list_widget, 1)

        list_actions = QHBoxLayout()
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear = QPushButton("Clear List")
        self.btn_clear.clicked.connect(self.clear_list)
        self.btn_sort_az = QPushButton("Sort A→Z")
        self.btn_sort_az.clicked.connect(lambda: self.sort_list(reverse=False))
        self.btn_sort_za = QPushButton("Sort Z→A")
        self.btn_sort_za.clicked.connect(lambda: self.sort_list(reverse=True))
        list_actions.addWidget(self.btn_remove)
        list_actions.addWidget(self.btn_clear)
        list_actions.addStretch(1)
        list_actions.addWidget(self.btn_sort_az)
        list_actions.addWidget(self.btn_sort_za)
        root.addLayout(list_actions)

        # Options box
        opts_box = QGroupBox("Options")
        form = QFormLayout(opts_box)
        self.spin_max_w = QSpinBox()
        self.spin_max_w.setRange(0, 20000)
        self.spin_max_w.setValue(0)
        self.spin_max_w.setSuffix(" px")
        self.spin_max_h = QSpinBox()
        self.spin_max_h.setRange(0, 20000)
        self.spin_max_h.setValue(0)
        self.spin_max_h.setSuffix(" px")
        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(36, 600)
        self.spin_dpi.setValue(72)
        self.chk_open_after = QCheckBox("Open file after save")
        form.addRow("Max width (0 = no resize)", self.spin_max_w)
        form.addRow("Max height (0 = no resize)", self.spin_max_h)
        form.addRow("PDF DPI", self.spin_dpi)
        form.addRow("", self.chk_open_after)
        root.addWidget(opts_box)

        # Convert + progress
        bottom = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.btn_convert = QPushButton("Convert to PDF…")
        self.btn_convert.clicked.connect(self.convert_to_pdf)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.cancel_conversion)
        self.btn_cancel.setVisible(False)
        bottom.addWidget(self.progress, 1)
        bottom.addStretch(1)
        bottom.addWidget(self.btn_convert)
        bottom.addWidget(self.btn_cancel)
        root.addLayout(bottom)

        # Styling
        self.setStyleSheet(
            """
            QWidget#Header {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #0d47a1, stop:1 #1976d2);
                border-radius: 10px;
            }
            QLineEdit { padding: 6px 8px; border: 1px solid #cfd8dc; border-radius: 6px; }
            QListWidget { border: 1px solid #e0e0e0; border-radius: 6px; }
            QPushButton { padding: 6px 12px; border-radius: 6px; }
            QGroupBox { border: 1px solid #e0e0e0; border-radius: 8px; margin-top: 12px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #0d47a1; }
            QProgressBar { border: 1px solid #cfd8dc; border-radius: 6px; text-align: center; }
            QProgressBar::chunk { background-color: #1976d2; }
            """
        )

    # ========== List management ==========
    def _add_paths(self, paths: Iterable[str]):
        added = 0
        pending: List[str] = []
        for p in paths:
            if os.path.isdir(p):
                try:
                    for f in os.listdir(p):
                        fp = os.path.join(p, f)
                        if os.path.isfile(fp) and os.path.splitext(fp)[1].lower() in self.allowed_exts:
                            pending.append(fp)
                except Exception:
                    pass
                self.path_edit.setText(p)
            else:
                if os.path.splitext(p)[1].lower() in self.allowed_exts and os.path.isfile(p):
                    pending.append(p)

        # Avoid duplicates based on absolute path
        existing = set(
            self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.list_widget.count())
        )
        for fp in pending:
            afp = os.path.abspath(fp)
            if afp in existing:
                continue
            item = QListWidgetItem(os.path.basename(afp))
            item.setToolTip(afp)
            item.setData(Qt.ItemDataRole.UserRole, afp)
            self.list_widget.addItem(item)
            existing.add(afp)
            added += 1

        if added:
            self.statusBar().showMessage(f"Added {added} item(s). Drag to reorder.", 3000)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Images Folder")
        if folder:
            self._add_paths([folder])

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Image Files",
            "",
            "Images (*.jpg *.jpeg *.png *.jfif)",
        )
        if files:
            self._add_paths(files)

    def remove_selected(self):
        for item in self.list_widget.selectedItems():
            row = self.list_widget.row(item)
            self.list_widget.takeItem(row)

    def clear_list(self):
        self.list_widget.clear()

    def sort_list(self, reverse: bool = False):
        items = [self.list_widget.item(i) for i in range(self.list_widget.count())]
        items.sort(key=lambda it: natural_key(it.text()), reverse=reverse)
        self.list_widget.clear()
        for it in items:
            self.list_widget.addItem(it)

    def _current_paths(self) -> List[str]:
        return [
            self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self.list_widget.count())
        ]

    # ========== Conversion ==========
    def convert_to_pdf(self):
        paths = self._current_paths()
        if not paths:
            QMessageBox.information(self, "Image2PDF", "Please add images first.")
            return

        base_dir = os.path.dirname(paths[0]) if paths else os.path.expanduser("~")
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF As",
            os.path.join(base_dir, "output.pdf"),
            "PDF Files (*.pdf)",
        )
        if not save_path:
            return

        self._disable_ui_for_work(True)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_cancel.setVisible(True)

        self._thread = QThread(self)
        self._worker = ConvertWorker(
            paths=paths,
            save_path=save_path,
            max_w=int(self.spin_max_w.value()),
            max_h=int(self.spin_max_h.value()),
            dpi=int(self.spin_dpi.value()),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.canceled.connect(self._on_canceled)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._worker.canceled.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_worker)
        self._save_path = save_path
        self._thread.start()

    def cancel_conversion(self):
        if hasattr(self, "_worker") and self._worker:
            self._worker.cancel()

    def _on_progress(self, i: int, total: int, name: str):
        pct = int(i * 100 / max(1, total))
        self.progress.setValue(pct)
        self.statusBar().showMessage(f"Processing {i}/{total}: {name}")

    def _on_finished(self, save_path: str):
        self.progress.setVisible(False)
        self.btn_cancel.setVisible(False)
        self._disable_ui_for_work(False)
        self.statusBar().showMessage(f"PDF saved to: {save_path}", 5000)
        QMessageBox.information(self, "Image2PDF", f"PDF saved to:\n{save_path}")
        if self.chk_open_after.isChecked():
            try:
                if sys.platform.startswith("win"):
                    os.startfile(save_path)  # type: ignore[attr-defined]
                elif sys.platform == "darwin":
                    os.system(f'open "{save_path}"')
                else:
                    os.system(f'xdg-open "{save_path}"')
            except Exception:
                pass

    def _on_error(self, msg: str):
        self.progress.setVisible(False)
        self.btn_cancel.setVisible(False)
        self._disable_ui_for_work(False)
        self.statusBar().showMessage("Conversion failed.", 5000)
        QMessageBox.critical(self, "Image2PDF", f"Conversion failed:\n{msg}")

    def _on_canceled(self):
        self.progress.setVisible(False)
        self.btn_cancel.setVisible(False)
        self._disable_ui_for_work(False)
        self.statusBar().showMessage("Conversion canceled.", 3000)

    def _cleanup_worker(self):
        try:
            self._worker.deleteLater()
        except Exception:
            pass
        try:
            self._thread.deleteLater()
        except Exception:
            pass

    def _disable_ui_for_work(self, busy: bool):
        widgets = [
            self.path_edit,
            self.list_widget,
            self.btn_remove,
            self.btn_clear,
            self.btn_sort_az,
            self.btn_sort_za,
            self.spin_max_w,
            self.spin_max_h,
            self.spin_dpi,
            self.chk_open_after,
            self.btn_convert,
        ]
        for w in widgets:
            w.setDisabled(busy)


def main():
    app = QApplication(sys.argv)
    QApplication.setStyle(QStyleFactory.create("Fusion"))
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
