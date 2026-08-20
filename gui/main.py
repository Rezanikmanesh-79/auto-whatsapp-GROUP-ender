import sys

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WhatsApp Group Sender")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("WhatsApp Automation")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())