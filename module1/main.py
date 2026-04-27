import sys
import json
import os
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QPainter, QColor, QPen, QIcon, QPixmap, QTransform
from PyQt6.QtCore import Qt, QSize

M = os.path.join("Прил_В1_КОД 09.02.08-1-2026-М1", "media")
LOGO = os.path.join(M, "TLgreen.png")
IMG1, IMG2, IMG3, IMG4, IMG5 = (
    os.path.join(M, "Cbottom.png"),
    os.path.join(M, "Pedestrain.png"),
    os.path.join(M, "Block.png"),
    os.path.join(M, "Zhorizontal.png"),
    os.path.join(M, "TLyellow.png")
)
RD1, RD2 = os.path.join(M, "Rvertical.png"), os.path.join(M, "Rcrossroads.png")
PLACE_IMGS = [IMG1, IMG2, IMG3, IMG4, IMG5]
ROAD_IMGS = [RD1, RD2]
FREE = {IMG2, IMG3}
ROT = {IMG1, IMG2, IMG4, IMG5, RD1, RD2}
CYCLES = {
    IMG1: [IMG1, os.path.join(M, "BCvertical.png"), os.path.join(M, "GCicon.ico")],
    IMG3: [IMG3, os.path.join(M, "Stop.png"), os.path.join(M, "Start.png")],
    IMG5: [IMG5, os.path.join(M, "TLred.png"), os.path.join(M, "TLgreen.png")],
}
CELL, COLS, ROWS = 36, 21, 21

def px(path, rot=0):
    """Загрузка изображения с поворотом и проверкой существования"""
    if not os.path.exists(path):
        pixmap = QPixmap(CELL, CELL)
        pixmap.fill(Qt.GlobalColor.lightGray)
        return pixmap
    
    p = QPixmap(path)
    if p.isNull():
        pixmap = QPixmap(CELL, CELL)
        pixmap.fill(Qt.GlobalColor.lightGray)
        return pixmap
    
    if rot and rot % 360 != 0:
        return p.transformed(QTransform().rotate(rot))
    return p


class Grid(QWidget):
    def __init__(self, side):
        super().__init__()
        self.setFixedSize(COLS * CELL, ROWS * CELL)
        self.side = side
        self.roads = {}
        self.objs = {}
        self.mode = None
        self.sel = None
        self._is_valid = True

    def paintEvent(self, event):
        if not self._is_valid:
            return
            
        try:
            p = QPainter(self)
            if not p.isActive():
                return
                
            p.fillRect(self.rect(), QColor(235, 235, 235))
            
            # Сначала рисуем дороги (нижний слой)
            for (x, y), o in self.roads.items():
                img = px(o["path"], o.get("rot", 0))
                if not img.isNull():
                    p.drawPixmap(x * CELL, y * CELL, CELL, CELL, img)
            
            # Затем рисуем объекты (верхний слой)
            for (x, y), o in self.objs.items():
                img = px(o["path"], o.get("rot", 0))
                if not img.isNull():
                    p.drawPixmap(x * CELL, y * CELL, CELL, CELL, img)
            
            # Рисуем сетку
            p.setPen(QPen(QColor(0, 0, 0, 50), 1))
            for c in range(COLS + 1):
                p.drawLine(c * CELL, 0, c * CELL, ROWS * CELL)
            for r in range(ROWS + 1):
                p.drawLine(0, r * CELL, COLS * CELL, r * CELL)
                
        except RuntimeError:
            pass

    def mousePressEvent(self, e):
        if not self._is_valid:
            return
            
        if e.button() != Qt.MouseButton.LeftButton:
            return
            
        x = int(e.position().x() // CELL)
        y = int(e.position().y() // CELL)
        
        if not (0 <= x < COLS and 0 <= y < ROWS):
            return
        c = (x, y)
        
        # Режим добавления дороги
        if self.mode == 'road' and self.sel:
            self.roads[c] = {"path": self.sel, "base": self.sel, "rot": 0}
            self.update()
        
        # Режим добавления объектов
        elif self.mode == 'place' and self.sel:
            # Свободные объекты (пешеходы и блоки) можно ставить где угодно
            if self.sel in FREE:
                self.objs[c] = {"path": self.sel, "base": self.sel, "rot": 0, "speed": 0}
            # Остальные объекты требуют наличие дороги под ними
            elif c in self.roads:
                self.objs[c] = {"path": self.sel, "base": self.sel, "rot": 0, "speed": 0}
            else:
                QMessageBox.information(self, "Внимание", "Сначала постройте дорогу в этой ячейке!")
                return
            self.update()
        
        # Просмотр свойств существующего объекта
        elif self.mode == 'place':
            o = self.objs.get(c) or self.roads.get(c)
            if o:
                self.side.show_props(c, o, self)

    def save(self, path):
        """Сохранение карты с валидацией"""
        try:
            data = {
                "roads": {f"{k[0]},{k[1]}": v for k, v in self.roads.items()},
                "objs": {f"{k[0]},{k[1]}": v for k, v in self.objs.items()}
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить файл: {str(e)}")
            return False

    def load(self, path):
        """Загрузка карты с валидацией"""
        try:
            if not os.path.exists(path):
                QMessageBox.warning(self, "Ошибка", "Файл не найден!")
                return False
                
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            def parse(d):
                result = {}
                for k, v in d.items():
                    try:
                        x, y = map(int, k.split(","))
                        result[(x, y)] = v
                    except (ValueError, TypeError):
                        continue
                return result
            
            self.roads = parse(data.get("roads", {}))
            self.objs = parse(data.get("objs", {}))
            self.update()
            return True
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "Ошибка", f"Неверный формат JSON: {str(e)}")
            return False
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить файл: {str(e)}")
            return False

    def closeEvent(self, event):
        self._is_valid = False
        self.roads.clear()
        self.objs.clear()
        event.accept()


class Side(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(120)
        self.grid = None
        self.ibtns = []
        self.vb = QVBoxLayout(self)
        self.sp = self._sec(PLACE_IMGS, "Объекты")
        self.sr = self._sec(ROAD_IMGS, "Дороги")
        self.props = QWidget()
        self.pvb = QVBoxLayout(self.props)
        
        for w in (self.sp, self.sr, self.props):
            w.hide()
            self.vb.addWidget(w)
        self.vb.addStretch()

    def _sec(self, paths, title):
        w = QWidget()
        vb = QVBoxLayout(w)
        
        title_label = QLabel(f"<b>{title}</b>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vb.addWidget(title_label)
        
        for p in paths:
            b = QPushButton()
            b.setFixedSize(100, 100)
            b.setCheckable(True)
            b.setProperty("path", p)
            base_name = os.path.basename(p).replace(".png", "").replace(".ico", "")
            b.setToolTip(base_name)
            
            ic = px(p)
            if not ic.isNull():
                b.setIcon(QIcon(ic))
                b.setIconSize(QSize(88, 88))
            else:
                b.setText(base_name[:8])
            
            b.clicked.connect(self._pick)
            vb.addWidget(b)
            self.ibtns.append(b)
        return w

    def _pick(self):
        if not self.grid or not self.grid._is_valid:
            return
            
        s = self.sender()
        for b in self.ibtns:
            if b is not s:
                b.setChecked(False)
        if self.grid:
            self.grid.sel = s.property("path") if s.isChecked() else None

    def switch(self, place=False, road=False):
        if not self.grid or not self.grid._is_valid:
            return
            
        for b in self.ibtns:
            b.setChecked(False)
        if self.grid:
            self.grid.sel = None
            self.grid.mode = 'place' if place else ('road' if road else None)
        self.props.hide()
        self.sp.setVisible(place)
        self.sr.setVisible(road)

    def show_props(self, cell, obj, grid):
        if not grid._is_valid:
            return
            
        while self.pvb.count():
            w = self.pvb.takeAt(0).widget()
            if w:
                w.deleteLater()
        
        self.props.show()
        base = obj.get("base", "")
        self.pvb.addWidget(QLabel(f"<b>{os.path.basename(base)}</b>"))
        self.pvb.addWidget(QLabel(f"Позиция: ({cell[0]}, {cell[1]})"))

        if base in ROT:
            b = QPushButton("Повернуть (90°)")
            def rotate():
                if grid._is_valid:
                    obj["rot"] = (obj.get("rot", 0) + 90) % 360
                    grid.update()
            b.clicked.connect(rotate)
            self.pvb.addWidget(b)

        if base in CYCLES:
            b = QPushButton("Изменить тип")
            c = CYCLES[base]
            def color():
                if grid._is_valid:
                    current = obj.get("path", base)
                    i = c.index(current) if current in c else 0
                    obj["path"] = c[(i + 1) % len(c)]
                    grid.update()
            b.clicked.connect(color)
            self.pvb.addWidget(b)

        if base == IMG2:
            speed_frame = QFrame()
            speed_layout = QVBoxLayout(speed_frame)
            
            lbl = QLabel(f"Скорость: {obj.get('speed', 0)}")
            speed_layout.addWidget(lbl)
            
            def update_speed(delta):
                if grid._is_valid:
                    new_speed = max(0, min(20, obj.get("speed", 0) + delta))
                    obj["speed"] = new_speed
                    lbl.setText(f"Скорость: {new_speed}")
                    grid.update()
            
            btn_layout = QHBoxLayout()
            b_plus = QPushButton("+")
            b_plus.clicked.connect(lambda: update_speed(1))
            b_minus = QPushButton("-")
            b_minus.clicked.connect(lambda: update_speed(-1))
            btn_layout.addWidget(b_minus)
            btn_layout.addWidget(b_plus)
            speed_layout.addLayout(btn_layout)
            
            self.pvb.addWidget(speed_frame)

        b_del = QPushButton("Удалить")
        def dele():
            if grid._is_valid:
                grid.objs.pop(cell, None)
                grid.roads.pop(cell, None)
                grid.update()
                self.props.hide()
        b_del.clicked.connect(dele)
        self.pvb.addWidget(b_del)


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Интеллектуальная Дорожная Система")
        
        if os.path.exists(LOGO):
            lp = QPixmap(LOGO)
            if not lp.isNull():
                self.setWindowIcon(QIcon(lp))
        
        self.side = Side()
        self.grid = Grid(self.side)
        self.side.grid = self.grid

        c = QWidget()
        self.setCentralWidget(c)
        root = QVBoxLayout(c)
        body = QHBoxLayout()
        body.addWidget(self.side)
        body.addWidget(self.grid)
        root.addLayout(body)

        bar = QHBoxLayout()
        self.bp = QPushButton("Добавить объекты")
        self.bp.setCheckable(True)
        self.br = QPushButton("Редактор дороги")
        self.br.setCheckable(True)
        bs = QPushButton("Сохранить")
        bl = QPushButton("Загрузить")
        
        self.bp.toggled.connect(lambda v: (self.br.setChecked(False), self.side.switch(place=v)))
        self.br.toggled.connect(lambda v: (self.bp.setChecked(False), self.side.switch(road=v)))
        bs.clicked.connect(self._save)
        bl.clicked.connect(self._load)
        
        for b in (self.bp, self.br, bs, bl):
            bar.addWidget(b)
        root.addLayout(bar)
        
        self.setMinimumSize(COLS * CELL + 130, ROWS * CELL + 50)
        self.adjustSize()

    def _save(self):
        if not self.grid._is_valid:
            return
        fn, _ = QFileDialog.getSaveFileName(self, "Сохранить карту", "", "JSON (*.json)")
        if fn:
            self.grid.save(fn)

    def _load(self):
        if not self.grid._is_valid:
            return
        fn, _ = QFileDialog.getOpenFileName(self, "Загрузить карту", "", "JSON (*.json)")
        if fn:
            self.grid.load(fn)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())