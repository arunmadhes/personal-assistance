import sys
from PySide6.QtWidgets import QApplication
from irish_ui import IrishUI


def main():

    app = QApplication(sys.argv)

    window = IrishUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()