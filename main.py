import sys
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from gui.app import SaraUltra

if __name__ == "__main__":
    print("SARA Assistant Started...")
    app = SaraUltra()
    app.mainloop()