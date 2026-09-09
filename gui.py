import json
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QSettings
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QMessageBox, QComboBox
from subscription import fetch_subscription
from runner import run_tests, save_results

ROOT = Path(__file__).resolve().parent
STYLE = """
QMainWindow,QWidget{background:#090d12;color:#e9eef5;font-family:Segoe UI;} QFrame#card{background:#111821;border:1px solid #202b36;border-radius:16px;}
QLabel#title{font-size:30px;font-weight:800;color:#fff;} QLabel#subtitle,QLabel#muted{color:#8d9aaa;} QLabel#metric{font-size:25px;font-weight:800;color:#fff;}
QPlainTextEdit,QComboBox{background:#0d131a;border:1px solid #2b3947;border-radius:11px;padding:10px;color:#fff;}
QPlainTextEdit:focus,QComboBox:focus{border:1px solid #5f9dff;} QPushButton{background:#2f7df6;border:0;border-radius:10px;padding:11px 18px;font-weight:700;color:#fff;}
QPushButton:hover{background:#438cff;} QPushButton:disabled{background:#26313d;color:#6f7c89;} QPushButton#secondary{background:#1a232d;border:1px solid #2b3947;}
QTableWidget{background:#0e141b;border:1px solid #202b36;border-radius:12px;gridline-color:#1b2630;} QHeaderView::section{background:#151e27;color:#aebbc8;padding:10px;border:0;}
QProgressBar{background:#18212a;border:0;border-radius:6px;height:10px;text-align:center;} QProgressBar::chunk{background:#2f7df6;border-radius:6px;}
"""

class FetchWorker(QThread):
    success=Signal(object); failed=Signal(str)
    def __init__(self, urls): super().__init__(); self.urls=urls
    def run(self):
        try:
            all_configs=[]; errors=[]; seen=set()
            for source,url in enumerate(self.urls,1):
                try:
                    configs=fetch_subscription(url)
                    for cfg in configs:
                        if cfg.uri in seen: continue
                        seen.add(cfg.uri); cfg.source=f"ساب {source}"; cfg.index=len(all_configs)+1; all_configs.append(cfg)
                except Exception as exc: errors.append(f"ساب {source}: {exc}")
            if not all_configs: raise ValueError("هیچ کانفیگی از ساب‌ها دریافت نشد.\n"+"\n".join(errors))
            self.success.emit((all_configs,errors))
        except Exception as exc: self.failed.emit(str(exc))

class TestWorker(QThread):
    result=Signal(object); finished_ok=Signal(object); failed=Signal(str)
    def __init__(self,configs,settings,xray_path,endpoints,test_mode):
        super().__init__(); self.configs=configs; self.settings=settings; self.xray_path=xray_path; self.endpoints=endpoints; self.test_mode=test_mode
    def run(self):
        try:
            results=run_tests(self.configs,self.settings,self.xray_path,self.endpoints,self.test_mode,lambda r,done,total:self.result.emit((r,done,total)))
            self.finished_ok.emit(results)
        except Exception as exc: self.failed.emit(str(exc))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.configs=[]; self.results=[]; self.result_map={}; self.worker=None; self.tworker=None
        self.settings=json.loads((ROOT/"settings.json").read_text(encoding="utf-8")); self.user_settings=QSettings("ZMOBUP","ZMOBUP")
        self.setWindowTitle("ZMOBUP • V2Ray Speed Tester"); self.resize(1280,820); self.setMinimumSize(1050,700); self.build_ui()

    def card(self,title,value):
        box=QFrame(); box.setObjectName("card"); lay=QVBoxLayout(box); lay.setContentsMargins(18,15,18,15); t=QLabel(title); t.setObjectName("muted"); v=QLabel(value); v.setObjectName("metric"); lay.addWidget(t); lay.addWidget(v); return box

    def build_ui(self):
        root=QWidget(); self.setCentralWidget(root); main=QVBoxLayout(root); main.setContentsMargins(28,24,28,24); main.setSpacing(14)
        head=QHBoxLayout(); brand=QVBoxLayout(); title=QLabel("ZMOBUP"); title.setObjectName("title"); sub=QLabel("V2Ray / Xray  •  Subscription Speed Intelligence"); sub.setObjectName("subtitle"); brand.addWidget(title); brand.addWidget(sub); head.addLayout(brand); head.addStretch(); self.status=QLabel("● READY"); self.status.setStyleSheet("color:#63d391;font-weight:800;"); head.addWidget(self.status,alignment=Qt.AlignmentFlag.AlignTop); main.addLayout(head)
        source=QFrame(); source.setObjectName("card"); sl=QVBoxLayout(source); sl.setContentsMargins(18,14,18,14); top=QHBoxLayout(); top.addWidget(QLabel("Subscription URL ها — هر لینک در یک خط")); top.addStretch(); self.mode=QComboBox(); self.mode.addItem("دانلود", "download"); self.mode.addItem("آپلود", "upload"); self.mode.addItem("دانلود + آپلود", "both"); self.mode.setCurrentIndex(int(self.user_settings.value("test_mode_index",2))); top.addWidget(QLabel("نوع تست:")); top.addWidget(self.mode); sl.addLayout(top)
        self.urls=QPlainTextEdit(); self.urls.setPlaceholderText("https://example.com/sub1\nhttps://example.com/sub2\nhttps://example.com/sub3"); self.urls.setPlainText(self.user_settings.value("subscription_urls", "")); self.urls.setMaximumHeight(92); sl.addWidget(self.urls)
        row=QHBoxLayout(); self.load_btn=QPushButton("دریافت همه ساب‌ها"); self.test_btn=QPushButton("شروع تست 🚀"); self.test_btn.setEnabled(False); self.stop_btn=QPushButton("توقف"); self.stop_btn.setObjectName("secondary"); self.stop_btn.setEnabled(False); row.addWidget(self.load_btn); row.addWidget(self.test_btn); row.addWidget(self.stop_btn); row.addStretch(); sl.addLayout(row); main.addWidget(source)
        metrics=QHBoxLayout(); metrics.setSpacing(14); self.m_received=self.card("کل کانفیگ‌ها","0"); self.m_tested=self.card("تست‌شده","0"); self.m_online=self.card("آنلاین","0"); self.m_top=self.card("Top 20","—"); [metrics.addWidget(x) for x in (self.m_received,self.m_tested,self.m_online,self.m_top)]; main.addLayout(metrics)
        pc=QFrame(); pc.setObjectName("card"); pl=QVBoxLayout(pc); prow=QHBoxLayout(); prow.addWidget(QLabel("وضعیت تست")); prow.addStretch(); self.progress_text=QLabel("همه ساب‌ها را وارد و دریافت کنید"); self.progress_text.setObjectName("muted"); prow.addWidget(self.progress_text); pl.addLayout(prow); self.progress=QProgressBar(); pl.addWidget(self.progress); main.addWidget(pc)
        tc=QFrame(); tc.setObjectName("card"); tl=QVBoxLayout(tc); tr=QHBoxLayout(); tr.addWidget(QLabel("نتایج — بعد از هر تست دوباره رتبه‌بندی می‌شود")); tr.addStretch(); self.best_btn=QPushButton("فقط بهترین‌ها"); self.best_btn.setObjectName("secondary"); self.export_btn=QPushButton("خروجی CSV"); self.export_btn.setObjectName("secondary"); tr.addWidget(self.best_btn); tr.addWidget(self.export_btn); tl.addLayout(tr)
        self.table=QTableWidget(0,9); self.table.setHorizontalHeaderLabels(["#","Remark","Protocol","ساب","Ping","Download","Upload","Score","Status"]); self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); tl.addWidget(self.table,1); main.addWidget(tc,1)
        foot=QLabel("ZMOBUP  •  همه لینک‌های ساب محلی ذخیره می‌شوند و به GitHub ارسال نمی‌شوند"); foot.setObjectName("subtitle"); main.addWidget(foot)
        self.load_btn.clicked.connect(self.load_configs); self.test_btn.clicked.connect(self.start_test); self.stop_btn.clicked.connect(self.stop_test); self.best_btn.clicked.connect(self.show_best); self.export_btn.clicked.connect(self.export_csv); self.mode.currentIndexChanged.connect(lambda i:self.user_settings.setValue("test_mode_index",i)); self.urls.textChanged.connect(lambda:self.user_settings.setValue("subscription_urls",self.urls.toPlainText()))

    def set_metric(self,card,value): card.findChildren(QLabel)[1].setText(str(value))
    def selected_mode(self): return self.mode.currentData()
    def load_configs(self):
        urls=[x.strip() for x in self.urls.toPlainText().splitlines() if x.strip()]
        if not urls: QMessageBox.warning(self,"ZMOBUP","حداقل یک لینک Subscription وارد کنید."); return
        self.user_settings.setValue("subscription_urls", "\n".join(urls)); self.load_btn.setEnabled(False); self.test_btn.setEnabled(False); self.status.setText("● FETCHING"); self.progress.setRange(0,0); self.progress_text.setText(f"در حال دریافت {len(urls)} ساب...")
        self.worker=FetchWorker(urls); self.worker.success.connect(self.on_configs); self.worker.failed.connect(self.on_fetch_error); self.worker.finished.connect(lambda:self.load_btn.setEnabled(True)); self.worker.start()

    def on_configs(self,payload):
        configs,errors=payload; self.configs=configs; self.results=[]; self.result_map={}; self.set_metric(self.m_received,len(configs)); self.set_metric(self.m_tested,0); self.set_metric(self.m_online,0); self.set_metric(self.m_top,"—"); self.progress.setRange(0,100); self.progress.setValue(100); self.render_rows()
        self.status.setText("● READY"); self.status.setStyleSheet("color:#63d391;font-weight:800;"); self.progress_text.setText(f"{len(configs)} کانفیگ از {len(set(getattr(c,'source','') for c in configs))} ساب آماده است"); self.test_btn.setEnabled(True)
        if errors: QMessageBox.warning(self,"برخی ساب‌ها دریافت نشدند","\n".join(errors))

    def on_fetch_error(self,msg):
        self.progress.setRange(0,100); self.progress.setValue(0); self.status.setText("● ERROR"); self.progress_text.setText("خطا در دریافت Subscription"); QMessageBox.critical(self,"خطا",msg)

    def render_rows(self):
        items=[]
        for c in self.configs:
            r=self.result_map.get(c.index)
            if r: items.append(r)
            else: items.append({"index":c.index,"remark":c.remark,"protocol":c.protocol,"source":getattr(c,"source",""),"status":"QUEUED","score":-1})
        def rank(r):
            done=r.get("status")!="QUEUED"; online=r.get("status")=="ONLINE"
            return (done,online,r.get("score",-1))
        items.sort(key=rank,reverse=True); self.table.setRowCount(0)
        for r in items:
            row=self.table.rowCount(); self.table.insertRow(row); vals=[r.get("index","—"),r.get("remark",""),r.get("protocol",""),r.get("source",""),r.get("latency_ms") if r.get("latency_ms") is not None else "—",r.get("download_mbps") if r.get("download_mbps") is not None else "—",r.get("upload_mbps") if r.get("upload_mbps") is not None else "—",r.get("score") if r.get("score") is not None and r.get("score") >= 0 else "—",r.get("status","READY")]
            for col,val in enumerate(vals): self.table.setItem(row,col,QTableWidgetItem(str(val)))

    def update_result(self,payload):
        r,done,total=payload; self.result_map[r["index"]]=r; self.results=list(self.result_map.values()); self.render_rows(); self.progress.setValue(int(done*100/max(total,1))); self.progress_text.setText(f"{done} از {total} تست شد • رتبه‌بندی به‌روز شد"); self.set_metric(self.m_tested,done); self.set_metric(self.m_online,sum(x.get("status")=="ONLINE" for x in self.results)); self.set_metric(self.m_top,min(len(self.results),int(self.settings["test"].get("top_n",20))))

    def start_test(self):
        if not self.configs: return
        self.results=[]; self.result_map={}; self.render_rows(); s=self.settings["test"]; mode=self.selected_mode(); self.status.setText(f"● TESTING • {mode.upper()}"); self.status.setStyleSheet("color:#6ea8ff;font-weight:800;"); self.progress.setValue(0); self.test_btn.setEnabled(False); self.load_btn.setEnabled(False); self.stop_btn.setEnabled(True)
        self.tworker=TestWorker(self.configs,s,self.settings["xray_path"],self.settings["endpoints"],mode); self.tworker.result.connect(self.update_result); self.tworker.finished_ok.connect(self.on_test_done); self.tworker.failed.connect(self.on_test_error); self.tworker.start()

    def stop_test(self):
        if self.tworker and self.tworker.isRunning(): self.tworker.requestInterruption(); self.tworker.terminate(); self.tworker.wait(1500)
        self.stop_btn.setEnabled(False); self.test_btn.setEnabled(bool(self.configs)); self.load_btn.setEnabled(True); self.status.setText("● STOPPED"); self.progress_text.setText("تست متوقف شد")

    def on_test_done(self,results):
        self.results=results; self.result_map={r["index"]:r for r in results}; self.render_rows(); top=save_results(results,int(self.settings["test"].get("top_n",20))); self.set_metric(self.m_top,len(top)); self.set_metric(self.m_online,sum(x.get("status")=="ONLINE" for x in results)); self.status.setText("● COMPLETE"); self.status.setStyleSheet("color:#63d391;font-weight:800;"); self.progress.setValue(100); self.progress_text.setText(f"تست کامل شد • {len(results)} نتیجه ذخیره شد"); self.stop_btn.setEnabled(False); self.test_btn.setEnabled(True); self.load_btn.setEnabled(True)

    def on_test_error(self,msg):
        self.stop_btn.setEnabled(False); self.test_btn.setEnabled(True); self.load_btn.setEnabled(True); self.status.setText("● ERROR"); self.progress_text.setText(msg); QMessageBox.critical(self,"خطای تست",msg)

    def show_best(self):
        if not self.results: return
        ids={str(x["index"]) for x in sorted(self.results,key=lambda x:x.get("score",0),reverse=True)[:int(self.settings["test"].get("top_n",20))]}
        for row in range(self.table.rowCount()): self.table.setRowHidden(row,self.table.item(row,0).text() not in ids)

    def export_csv(self):
        path=ROOT/"results"/"latest.csv"; QMessageBox.information(self,"ZMOBUP",f"فایل خروجی:\n{path}" if path.exists() else "هنوز نتیجه‌ای ذخیره نشده است.")


def run():
    app=QApplication(sys.argv); app.setStyleSheet(STYLE); app.setFont(QFont("Segoe UI",10)); win=MainWindow(); win.show(); return app.exec()

if __name__=="__main__": raise SystemExit(run())
