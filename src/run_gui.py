import traceback

if __name__ == '__main__':
    try:
        from gui import roar_gui
        print('Imported gui.roar_gui, invoking main()')
        rc = roar_gui.main()
        print('roar_gui.main() returned', rc)
    except Exception:
        print('Exception while running GUI:')
        traceback.print_exc()
