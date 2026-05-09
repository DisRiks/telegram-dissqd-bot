import base64
from pathlib import Path

def main():
    assets_dir = Path(__file__).resolve().parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Простые 1x1 PNG-плейсхолдеры (прозрачные), чтобы можно было увидеть кнопки с изображениями
    placeholders = {
        "VelocitySvyaz.png": (
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
            )
        ),
        "FixSB.png": (
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
            )
        ),
    }

    for name, data in placeholders.items():
        path = assets_dir / name
        if not path.exists():
            with open(path, "wb") as f:
                f.write(data)
            print(f"Created placeholder image: {path}")
        else:
            print(f"Placeholder already exists: {path}")


if __name__ == "__main__":
    main()
