import sys
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QMessageBox
from subscription import fetch_subscription

STYLE="""QMainWindow,QWidget{background:#090d12;color:#e9eef5;font-family:Segoe UI;} QFrame#card{background:#111821;border:1px solid #202b36;border-radius:16px;} QLabel#title{font-size:30px;font-weight:800;color:#fff;} QLabel#subtitle,QLabel#muted{color:#8d9aaa;} QLabel#metric{font-size:25px;font-weight:800;color:#fff;} QLineEdit{background:#0d131a;border:1px solid #2b3947;border-radius:11px;padding:12px;color:#fff;} QLineEdit:focus{border:1px solid #5f9dff;} QPushButton{background:#2f7df6;border:0;border-radius:10px;padding:11px 18px;font-weight:700;color:#fff;} QPushButton:hover{background:#438cff;} QPushButton:disabled{background:#26313d;color:#6f7c89;} QPushButton#secondary{background:#1a232d;border:1px solid #2b3947;} QTableWidget{background:#0e141b;border:1px solid #202b36;border-radius:12px;gridline-color:#1b2630;} QHeaderView::section{background:#151e27;color:#aebbc8;padding:10px;border:0;} QProgressBar{background:#18212a;border:0;border-radius:6px;height:10px;text-align:center;} QProgressBar::chunk{background:#2f7df6;border-radius:6px;}"""

class FetchWorker(QThread):
    success=Signal(object); failed=Signal(str)
    def __init__(self,url): super().__init__(); self.url=url
    def run(self):
        try:self.success.emit(fetch_subscription(self.url))
        except Exception as exc:self.failed.emit(str(exc))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.configs=[]; self.worker=None
        self.setWindowTitle("ZMOBUP • V2Ray Speed Tester"); self.resize(1280,820); self.setMinimumSize(1050,700); self.build_ui()
    def card(self,title,value):
        box=QFrame(); box.setObjectName("card"); lay=QVBoxLayout(box); lay.setContentsMargins(18,15,18,15); t=QLabel(title); t.setObjectName("muted"); v=QLabel(value); v.setObjectName("metric"); lay.addWidget(t); lay.addWidget(v); return box
    def build_ui(self):
        root=QWidget(); self.setCentralWidget(root); main=QVBoxLayout(root); main.setContentsMargins(28,24,28,24); main.setSpacing(16)
        head=QHBoxLayout(); brand=QVBoxLayout(); title=QLabel("ZMOBUP"); title.setObjectName("title"); sub=QLabel("V2Ray / Xray  •  Subscription Speed Intelligence"); sub.setObjectName("subtitle"); brand.addWidget(title); brand.addWidget(sub); head.addLayout(brand); head.addStretch(); self.status=QLabel("● READY"); self.status.setStyleSheet("color:#63d391;font-weight:800;"); head.addWidget(self.status,alignment=Qt.AlignmentFlag.AlignTop); main.addLayout(head)
        source=QFrame(); source.setObjectName("card"); sl=QVBoxLayout(source); sl.setContentsMargins(18,15,18,15); sl.addWidget(QLabel("Subscription URL")); row=QHBoxLayout(); self.url=QLineEdit(); self.url.setPlaceholderText("https://example.com/subscription..."); self.load_btn=QPushButton("دریافت کانفیگ‌ها"); self.test_btn=QPushButton("شروع تست 🚀"); self.test_btn.setEnabled(False); row.addWidget(self.url,1); row.addWidget(self.load_btn); row.addWidget(self.test_btn); sl.addLayout(row); main.addWidget(source)
        metrics=QHBoxLayout(); metrics.setSpacing(14); self.m_received=self.card("کانفیگ‌های دریافت‌شده","0"); self.m_tested=self.card("تست‌شده","0"); self.m_online=self.card("آنلاین","0"); self.m_top=self.card("Top 20","—"); [metrics.addWidget(x) for x in (self.m_received,self.m_tested,self.m_online,self.m_top)]; main.addLayout(metrics)
        progress_card=QFrame(); progress_card.setObjectName("card"); pl=QVBoxLayout(progress_card); pl.setContentsMargins(18,14,18,14); prow=QHBoxLayout(); prow.addWidget(QLabel("وضعیت تست")); prow.addStretch(); self.progress_text=QLabel("لینک Subscription را وارد کنید"); self.progress_text.setObjectName("muted"); prow.addWidget(self.progress_text); pl.addLayout(prow); self.progress=QProgressBar(); self.progress.setValue(0); pl.addWidget(self.progress); main.addWidget(progress_card)
        table_card=QFrame(); table_card.setObjectName("card"); tl=QVBoxLayout(table_card); tl.setContentsMargins(12,12,12,12); tr=QHBoxLayout(); tr.addWidget(QLabel("نتایج کانفیگ‌ها")); tr.addStretch(); self.best_btn=QPushButton("فقط بهترین‌ها"); self.best_btn.setObjectName("secondary"); self.export_btn=QPushButton("خروجی CSV"); self.export_btn.setObjectName("secondary"); tr.addWidget(self.best_btn); tr.addWidget(self.export_btn); tl.addLayout(tr)
        self.table=QTableWidget(0,7); self.table.setHorizontalHeaderLabels(["#","Remark","Protocol","Ping","Download","Upload","Score"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); tl.addWidget(self.table,1); main.addWidget(table_card,1); footer=QLabel("ZMOBUP  •  Local-first testing  •  Subscription URL is never committed to GitHub"); footer.setObjectName("subtitle"); main.addWidget(footer)
        self.load_btn.clicked.connect(self.load_configs); self.test_btn.clicked.connect(self.start_test); self.best_btn.clicked.connect(self.show_best)
    def set_metric(self,card,value): card.findChildren(QLabel)[1].setText(str(value))
    def load_configs(self):
        url=self.url.text().strip()
        if not url: QMessageBox.warning(self,"ZMOBUP","لطفاً لینک Subscription را وارد کنید."); return
        self.load_btn.setEnabled(False); self.test_btn.setEnabled(False); self.status.setText("● FETCHING"); self.status.setStyleSheet("color:#6ea8ff;font-weight:800;"); self.progress_text.setText("در حال دریافت و Decode کردن..."); self.progress.setRange(0,0); self.worker=FetchWorker(url); self.worker.success.connect(self.on_configs); self.worker.failed.connect(self.on_fetch_error); self.worker.finished.connect(lambda:self.load_btn.setEnabled(True)); self.worker.start()
    def on_configs(self,configs):
        self.configs=configs; self.progress.setRange(0,100); self.progress.setValue(100); self.set_metric(self.m_received,len(configs)); self.set_metric(self.m_tested,0); self.set_metric(self.m_online,0); self.set_metric(self.m_top,"—"); self.table.setRowCount(0)
        for cfg in configs:
            row=self.table.rowCount(); self.table.insertRow(row); vals=[cfg.index,cfg.remark,cfg.protocol,"—","—","—","—"]
            for col,val in enumerate(vals): self.table.setItem(row,col,QTableWidgetItem(str(val)))
        self.status.setText("● READY"); self.status.setStyleSheet("color:#63d391;font-weight:800;"); self.progress_text.setText(f"{len(configs)} کانفیگ آماده تست است"); self.test_btn.setEnabled(True)
    def on_fetch_error(self,message):
        self.progress.setRange(0,100); self.progress.setValue(0); self.status.setText("● ERROR"); self.status.setStyleSheet("color:#ff6b6b;font-weight:800;"); self.progress_text.setText("خطا در دریافت Subscription"); QMessageBox.critical(self,"خطا",message)
    def start_test(self): QMessageBox.information(self,"مرحله بعد","موتور Xray و تست Ping / Download / Upload در مرحله بعد به همین رابط متصل می‌شود.")
    def show_best(self):
        if not self.configs:return
        for row in range(self.table.rowCount()): self.table.setRowHidden(row,row>=20)

def run():
    app=QApplication(sys.argv); app.setStyleSheet(STYLE); app.setFont(QFont("Segoe UI",10)); win=MainWindow(); win.show(); return app.exec()
if __name__=="__main__": raise SystemExit(run())
