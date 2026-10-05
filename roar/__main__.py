"""Run the desktop application with python -m roar."""


def main():
    import argparse
    from . import Design, Session
    parser = argparse.ArgumentParser(description="ROAR desktop / Python API")
    parser.add_argument("design", nargs="?", help="Saved .roar or design JSON file")
    parser.add_argument("--home", help="Checkout/assets root (defaults to ROAR_HOME)")
    options = parser.parse_args()
    design = Design.load(options.design) if options.design else None
    return Session(design, home=options.home).run()


if __name__ == "__main__":
    raise SystemExit(main())