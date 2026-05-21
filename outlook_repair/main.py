"""Entry point for the Outlook File Repair Tool."""

import sys


def main():
    try:
        from outlook_repair.gui.app import OutlookRepairApp
        app = OutlookRepairApp()
        app.run()
    except ImportError as e:
        print(f'Import error: {e}')
        print('Install dependencies: pip install -r requirements.txt')
        sys.exit(1)
    except Exception as e:
        print(f'Fatal error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
