import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar

ROOT = Path(__file__).resolve().parent

STYLE = """
QMainWindow, QWidget { background: #0b0f14; color: #e8edf3; font-family: Segoe UI; }
QFrame#card { background: #111820; border: 1px solid #202b36; border-radius: 16px; }
QLabel#title { font-size: 28px; font-weight: 700; color: #ffffff; }
QLabel#subtitle { color: #8c9aaa; font-size: 13px; }
QLabel#metric { font-size: 24px; font-weight: 700; color: #ffffff; }
QLabel#muted { color: #8c9aaa; }
QLineEdit { background: #0d131a; border: 1px solid #2a3744; border-radius: 10px; padding: 12px; color: #fff; }
QLineEdit:focus { border: 1px solid #6ea8ff; }
QPushButton { background: #2f7df6; border: 0; border-radius: 10px; padding: 11px 18px; font-weight: 600; color: white; }
QPushButton:hover { background: #438cff; }
QPushButton#secondary { background: #1a232d; border: 1px solid #2b3947; }
QTableWidget { background: #0f151c; border: 1px solid #202b36; border-radius: 12px; gridline-color: #1c2731; }
QHeaderView::section { background: #151e27; color: #aebbc8; padding: 10px; border: 0; }
QProgressBar { background: #18212a; border: 0; border-radius: 6px; height: 10px; text-align: center; }
QProgressBar::chunk { background: #2f7df6; border-radius: 6px; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZMOBUP • V2Ray Speed Tester")
        self.resize(1280, 820)
        self.setMinimumSize(1050, 700)
        self.build_ui()

    def card(self, title, value):
        box = QFrame(); box.setObjectName("card")
        lay = QVBoxLayout(box); lay.setContentsMargins(18, 16, 18, 16)
        t = QLabel(title); t.setObjectName("muted")
        v = QLabel(value); v.setObjectName("metric")
        lay.addWidget(t); lay.addWidget(v)
        return box

    def build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        main = QVBoxLayout(root); main.setContentsMargins(28, 24, 28, 24); main.setSpacing(18)
        head = QHBoxLayout(); brand = QVBoxLayout()
        title = QLabel("ZMOBUP"); title.setObjectName("title")
        sub = QLabel("V2Ray / Xray • Subscription Speed Intelligence"); sub.setObjectName("subtitle")
        brand.addWidget(title); brand.addWidget(sub); head.addLayout(brand); head.addStretch()
        status = QLabel("● READY"); status.setStyleSheet("color:#63d391;font-weight:700;"); head.addWidget(status, alignment=Qt.AlignmentFlag.AlignTop); main.addLayout(head)
        source = QFrame(); source.setObjectName("card"); sl = QVBoxLayout(source); sl.setContentsMargins(18, 16, 18, 16)
        sl.addWidget(QLabel("Subscription URL")); row = QHBoxLayout()
        self.url = QLineEdit(); self.url.setPlaceholderText("https://example.com/subscription...")
        load = QPushButton("دریافت کانفیگ‌ها"); test = QPushButton("شروع تست 🚀")
        row.addWidget(self.url, 1); row.addWidget(load); row.addWidget(test); sl.addLayout(row); main.addWidget(source)
        metrics = QHBoxLayout(); metrics.setSpacing(14)
        for title_text, value in [("کانفیگ‌های دریافت‌شده", "0"), ("تست‌شده", "0"), ("آنلاین", "0"), ("Top 20", "—")]: metrics.addWidget(self.card(title_text, value))
        main.addLayout(metrics)
        progress_card = QFrame(); progress_card.setObjectName("card"); pl = QVBoxLayout(progress_card); pl.setContentsMargins(18, 15, 18, 15)
        prow = QHBoxLayout(); prow.addWidget(QLabel("وضعیت تست")); prow.addStretch(); self.progress_text = QLabel("آماده شروع"); self.progress_text.setObjectName("muted"); prow.addWidget(self.progress_text); pl.addLayout(prow)
        self.progress = QProgressBar(); self.progress.setValue(0); pl.addWidget(self.progress); main.addWidget(progress_card)
        table_card = QFrame(); table_card.setObjectName("card"); tl = QVBoxLayout(table_card); tl.setContentsMargins(12, 12, 12, 12)
        tr = QHBoxLayout(); tr.addWidget(QLabel("نتایج کانفیگ‌ها")); tr.addStretch(); tr.addWidget(QPushButton("فقط بهترین‌ها")); export = QPushButton("خروجی CSV"); export.setObjectName("secondary"); tr.addWidget(export); tl.addLayout(tr)
        self.table = QTableWidget(0, 7); self.table.setHorizontalHeaderLabels(["#", "Remark", "Protocol", "Ping", "Download", "Upload", "Score"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); tl.addWidget(self.table, 1)
        main.addWidget(table_card, 1); footer = QLabel("ZMOBUP  •  Local-first testing  •  Subscription URL is never committed to GitHub"); footer.setObjectName("subtitle"); main.addWidget(footer)


def run():
    app = QApplication(sys.argv); app.setStyleSheet(STYLE); app.setFont(QFont("Segoe UI", 10)); win = MainWindow(); win.show(); return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
