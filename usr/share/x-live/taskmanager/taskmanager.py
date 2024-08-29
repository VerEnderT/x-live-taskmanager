import sys
import psutil
import time
import subprocess
import re
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
                             QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QSlider, 
                             QFormLayout, QPushButton, QMessageBox)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon

class TaskManager(QMainWindow):
    def __init__(self):
        super().__init__()

        # Fenster einrichten
        self.setWindowTitle('X-Live Taskmanager')
        self.setGeometry(100, 100, 500, 400)  # Standardgröße auf 500x400 setzen
        self.setMinimumSize(500,150)
        self.setWindowIcon(QIcon("/usr/share/pixmaps/x-live-taskmanager"))
        self.background_color()
        # Hauptlayout
        main_layout = QVBoxLayout()

        # Oberes Layout für CPU und RAM
        top_layout = QHBoxLayout()
        bottom_layout = QHBoxLayout()
        # Layout für die linke Seite (CPU)
        cpu_layout = QVBoxLayout()

        self.cpu_progress = QProgressBar()
        cpu_layout.addWidget(self.cpu_progress)

        self.cpu_label = QLabel('CPU Auslastung:')
        cpu_layout.addWidget(self.cpu_label)

        top_layout.addLayout(cpu_layout)

        # Layout für die rechte Seite (RAM)
        ram_layout = QVBoxLayout()

        self.ram_progress = QProgressBar()
        ram_layout.addWidget(self.ram_progress)

        self.ram_label = QLabel('RAM Auslastung:')
        ram_layout.addWidget(self.ram_label)

        top_layout.addLayout(ram_layout)

        # Oberes Layout dem Hauptlayout hinzufügen
        main_layout.addLayout(top_layout)

        # QTableWidget für die Prozesse hinzufügen
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(4)  # Vier Spalten: PID, Name, CPU, RAM
        self.process_table.setHorizontalHeaderLabels(['PID', 'Prozess', 'CPU (%)', 'RAM (MB)'])
        self.process_table.setColumnHidden(0, True)  # PID-Spalte unsichtbar
        self.process_table.verticalHeader().setVisible(False)  # Zeilennummerierung ausblenden
        self.update_process_table()
        self.process_table.resize(466, 300)  # Breite und Höhe nach Bedarf anpassen

        self.process_table.setStyleSheet("""
            QTableView::item { 
                border: none;  /* Entfernt die Umrandung der Zellen */
            }
            QTableView {
                gridline-color: transparent;  /* Entfernt die Gitternetzlinien */
            }
        """)
        
        
        # Sortierfunktion anpassen
        self.process_table.horizontalHeader().sectionClicked.connect(self.handle_sorting)

        # Zeilen auswählen
        self.process_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.process_table.itemSelectionChanged.connect(self.row_selected)


        main_layout.addWidget(self.process_table)

        slider_layout = QHBoxLayout()

        # Button für "Über" hinzufügen
        self.about_button = QPushButton('Über')
        self.about_button.clicked.connect(self.show_about_dialog)
        slider_layout.addWidget(self.about_button)

        # Schieberegler für die Aktualisierungsrate hinzufügen
        self.update_interval_slider = QSlider(Qt.Horizontal)
        self.update_interval_slider.setMinimum(1)  # Minimum: 1 Sekunde
        self.update_interval_slider.setMaximum(60)  # Maximum: 60 Sekunden
        self.update_interval_slider.setValue(5)  # Startwert: 1 Sekunde
        self.update_interval_slider.setTickInterval(0)
        #self.update_interval_slider.setTickPosition(QSlider.TicksBelow)
        self.update_interval_slider.valueChanged.connect(self.update_interval_changed)

        self.slider_label = QLabel('Aktualisierungsrate: 1 Sekunde')
        slider_layout.addWidget(self.slider_label)
        slider_layout.addWidget(self.update_interval_slider)

        # Button zum Beenden des Prozesses hinzufügen
        self.terminate_button = QPushButton('Prozess beenden')
        self.terminate_button.clicked.connect(self.terminate_process)
        slider_layout.addWidget(self.terminate_button)

        # Slider Layout dem Hauptlayout hinzufügen
        main_layout.addLayout(slider_layout)

        # Zentrales Widget setzen
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Timer zum Aktualisieren der Systeminformationen
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_system_info)
        self.update_interval_changed(self.update_interval_slider.value())  # Setze initiale Aktualisierungsrate

        self.current_sort_column = 2  # cpu ist standardmäßig sortiert
        self.sort_order = Qt.DescendingOrder # absteigen ist standardmäßig sortiert
        self.selected_pid = None
        self.update_system_info()

    def handle_sorting(self, index):
        # Sortierreihenfolge umkehren
        if self.current_sort_column == index:
            self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            self.current_sort_column = index
            self.sort_order = Qt.AscendingOrder

        # Benutzerdefinierte Sortierung für die Tabelle
        self.sort_table(index)


    def sort_table(self, column):
        rows = []
        for row in range(self.process_table.rowCount()):
            row_data = []
            for col in range(self.process_table.columnCount()):  # Alle Spalten
                item = self.process_table.item(row, col)
                row_data.append(item.text() if item else "")
            rows.append((row, row_data))

        # Bestimme den Sortierkey basierend auf der Spalte
        try:
            rows.sort(key=lambda x: float(x[1][column]), reverse=self.sort_order == Qt.DescendingOrder)
        except ValueError:
            rows.sort(key=lambda x: x[1][column], reverse=self.sort_order == Qt.DescendingOrder)

        self.process_table.setRowCount(0)
        for row_index, row_data in rows:
            self.process_table.insertRow(self.process_table.rowCount())
            for col, data in enumerate(row_data):
                item = QTableWidgetItem(data)
                if col in [2, 3]:  # CPU und RAM rechtsbündig
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.process_table.setItem(self.process_table.rowCount() - 1, col, item)

        # Wiederherstellen der Sortierreihenfolge
        self.process_table.horizontalHeader().setSortIndicator(self.current_sort_column, self.sort_order)
        self.process_table.horizontalHeader().setSortIndicatorShown(True)

    def adjust_column_widths(self):
        total_width = self.process_table.viewport().width()
        # Setze die Spaltenbreiten als Prozentsätze der Gesamtbreite
        self.process_table.setColumnWidth(1, int(total_width * 0.65))  # Name (50%)
        self.process_table.setColumnWidth(2, int(total_width * 0.15))  # CPU (25%)
        self.process_table.setColumnWidth(3, int(total_width * 0.20))  # RAM (25%)

    def update_system_info(self):
        # Theme Farbe anpassen
        self.background_color()
        # Speicher aktuelle Sortierparameter
        current_sort_column = self.current_sort_column
        sort_order = self.sort_order

        # CPU- und RAM-Auslastung abrufen
        cpu_usage = psutil.cpu_percent(interval=1)

        # RAM-Informationen abrufen
        ram_info = psutil.virtual_memory()
        ram_usage_percent = ram_info.percent
        ram_usage = ram_info.used / 1_000_000  # Used RAM in MB
        ram_total = ram_info.total / 1_000_000  # Total RAM in MB

        # Labels und Fortschrittsbalken aktualisieren
        self.cpu_label.setText(f'CPU Auslastung: {cpu_usage}%')
        self.cpu_progress.setValue(int(cpu_usage))

        # RAM Label in MB anzeigen
        self.ram_label.setText(f'RAM Auslastung: {ram_usage:.2f} MB / {ram_total:.2f} MB')
        self.ram_progress.setValue(int(ram_usage_percent))

        # Prozessliste aktualisieren
        self.update_process_table()

        # Spaltenbreiten anpassen
        self.adjust_column_widths()

        # Sortierstatus wiederherstellen
        self.current_sort_column = current_sort_column
        self.sort_order = sort_order
        self.sort_table(self.current_sort_column)

    def update_process_table(self):
        # Alle Zeilen entfernen
        self.process_table.setRowCount(0)

        # Durch alle laufenden Prozesse iterieren
        for process in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            try:
                # Prozessinformationen abrufen
                pid = process.info['pid']
                name = process.info['name']
                cpu_percent = process.info['cpu_percent']
                memory_usage = process.info['memory_info'].rss / 1_000_000  # RSS (Resident Set Size) in MB

                # Neue Zeile hinzufügen
                row_position = self.process_table.rowCount()
                self.process_table.insertRow(row_position)

                # Prozessinformationen in die Zeile einfügen
                pid_item = QTableWidgetItem(str(pid))
                name_item = QTableWidgetItem(name)
                cpu_item = QTableWidgetItem(f'{cpu_percent:.1f}')
                ram_item = QTableWidgetItem(f'{memory_usage:.2f}')

                # Setze die Textausrichtung für CPU und RAM auf rechtsbündig
                cpu_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                ram_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                self.process_table.setItem(row_position, 0, pid_item)  # PID
                self.process_table.setItem(row_position, 1, name_item)  # Name
                self.process_table.setItem(row_position, 2, cpu_item)  # CPU
                self.process_table.setItem(row_position, 3, ram_item)  # RAM

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Fehler ignorieren, falls der Prozess während der Abfrage beendet wurde
                pass
                
    def row_selected(self):
        selected_items = self.process_table.selectedItems()
        if selected_items:
            # Nehme den PID-Wert aus der ersten Spalte der selektierten Zeile
            row = selected_items[0].row()
            pid_item = self.process_table.item(row, 0)
            if pid_item:
                # Versuch den PID-Wert zu extrahieren
                self.selected_pid = pid_item.text()

    def terminate_process(self):
        if self.selected_pid:
            try:
                # Beende den Prozess
                pid = int(self.selected_pid)
                process = psutil.Process(pid)
                process.terminate()
                process.wait()  # Warten bis der Prozess beendet ist
                QMessageBox.information(self, 'Erfolg', f'Prozess {pid} wurde beendet.')
                self.selected_pid = None
                self.update_system_info()  # Tabelle neu laden
            except psutil.NoSuchProcess:
                QMessageBox.warning(self, 'Fehler', f'Prozess {self.selected_pid} nicht gefunden.')
            except psutil.AccessDenied:
                QMessageBox.warning(self, 'Fehler', f'Zugriff verweigert für Prozess {self.selected_pid}.')
            except Exception as e:
                QMessageBox.warning(self, 'Fehler', f'Fehler beim Beenden des Prozesses {self.selected_pid}: {str(e)}')

    def update_interval_changed(self, value):
        # Aktualisierungsrate ändern (in Sekunden)
        self.timer.setInterval(value * 1000)  # Umrechnung von Sekunden auf Millisekunden
        # Aktualisieren des Labels des Sliders
        self.slider_label.setText(f'Aktualisierungsrate: {value} Sekunde(n)')

        # Sicherstellen, dass der Timer läuft
        if not self.timer.isActive():
            self.timer.start()
            
            
    def resizeEvent(self, event):
        super(TaskManager, self).resizeEvent(event)  # Basis-Methode aufrufen
        self.adjust_column_widths()  # Spaltenbreiten anpassen

    
    # Farbprofil abrufen und anwenden

    def get_current_theme(self):
        try:
            # Versuche, das Theme mit xfconf-query abzurufen
            result = subprocess.run(['xfconf-query', '-c', 'xsettings', '-p', '/Net/ThemeName'], capture_output=True, text=True)
            theme_name = result.stdout.strip()
            if theme_name:
                return theme_name
        except FileNotFoundError:
            print("xfconf-query nicht gefunden. Versuche gsettings.")
        except Exception as e:
            print(f"Error getting theme with xfconf-query: {e}")

        try:
            # Fallback auf gsettings, falls xfconf-query nicht vorhanden ist
            result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'], capture_output=True, text=True)
            theme_name = result.stdout.strip().strip("'")
            if theme_name:
                return theme_name
        except Exception as e:
            print(f"Error getting theme with gsettings: {e}")

        return None

    def extract_color_from_css(self,css_file_path, color_name):
        try:
            with open(css_file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                #print(content)
                # Muster zum Finden der Farbe
                pattern = r'{}[\s:]+([#\w]+)'.format(re.escape(color_name))
                match = re.search(pattern, content)
                if match:
                    return match.group(1)
                return None
        except IOError as e:
            print(f"Error reading file: {e}")
            return None
            
            
    def background_color(self):
        theme_name = self.get_current_theme()
        if theme_name:
            #print(f"Current theme: {theme_name}")

            # Pfad zur GTK-CSS-Datei des aktuellen Themes
            css_file_path = f'/usr/share/themes/{theme_name}/gtk-3.0/gtk.css'
            if os.path.exists(css_file_path):
                bcolor = self.extract_color_from_css(css_file_path, ' background-color')
                color = self.extract_color_from_css(css_file_path, ' color')
                self.setStyleSheet(f"background: {bcolor};color: {color}")
            else:
                print(f"CSS file not found: {css_file_path}")
        else:
            print("Unable to determine the current theme.")

    def show_about_dialog(self):
        # Extrahiere die Version aus dem apt show-Befehl
        version = self.get_version_info()
        
        # Über Fenster anzeigen
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Über X-Live Taskmanager")
        msg_box.setTextFormat(Qt.RichText)  # Setze den Textformatierungsmodus auf RichText (HTML)
        msg_box.setText(f"X-Live Taskmanager<br><br>"
                        f"Autor: VerEnderT aka F. Maczollek<br>"
                        f"Webseite: <a href='https://github.com/verendert/x-live-taskmanager'>https://github.com/verendert/x-live-taskmanager</a><br>"
                        f"Version: {version}<br><br>"
                        f"Copyright © 2024 VerEnderT<br>"
                        f"Dies ist freie Software; Sie können es unter den Bedingungen der GNU General Public License Version 3 oder einer späteren Version weitergeben und/oder modifizieren.<br>"
                        f"Dieses Programm wird in der Hoffnung bereitgestellt, dass es nützlich ist, aber OHNE JEDE GARANTIE; sogar ohne die implizite Garantie der MARKTGÄNGIGKEIT oder EIGNUNG FÜR EINEN BESTIMMTEN ZWECK.<br><br>"
                        f"Sie sollten eine Kopie der GNU General Public License zusammen mit diesem Programm erhalten haben. Wenn nicht, siehe <a href='https://www.gnu.org/licenses/'>https://www.gnu.org/licenses/</a>.")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec_()


    def get_version_info(self):
        try:
            result = subprocess.run(['apt', 'show', 'x-live-taskmanager'], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
        except Exception as e:
            print(f"Fehler beim Abrufen der Version: {e}")
        return "Unbekannt"

            
            

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TaskManager()
    window.show()
    sys.exit(app.exec_())
