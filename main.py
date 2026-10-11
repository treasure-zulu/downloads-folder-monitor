
import os
import time
import shutil
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from plyer import notification


# Use the current Windows user's home directory
HOME = Path.home()
DOWNLOADS_FOLDER = HOME / "Downloads"
DOCUMENTS_FOLDER = HOME / "Documents"


def notify_user(title, message):
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="Folder Monitor",
            timeout=5,
        )
    except Exception as error:
        print(f"Notification error: {error}")


def wait_until_ready(file_path, timeout=60):
    """Wait until a file exists and its size stops changing."""
    deadline = time.time() + timeout
    previous_size = -1
    stable_checks = 0

    while time.time() < deadline:
        if not file_path.exists() or not file_path.is_file():
            time.sleep(1)
            continue

        try:
            current_size = file_path.stat().st_size

            if current_size > 0 and current_size == previous_size:
                stable_checks += 1
                if stable_checks >= 2:
                    return True
            else:
                stable_checks = 0

            previous_size = current_size

        except OSError:
            stable_checks = 0

        time.sleep(1)

    return False


def move_pdf(file_path):
    file_path = Path(file_path)

    if file_path.suffix.lower() != ".pdf":
        return

    if not file_path.exists():
        return

    print(f"PDF detected: {file_path}")

    if not wait_until_ready(file_path):
        print(f"File did not become ready in time: {file_path}")
        return

    try:
        DOCUMENTS_FOLDER.mkdir(parents=True, exist_ok=True)

        destination = DOCUMENTS_FOLDER / file_path.name

        # Avoid overwriting an existing document
        if destination.exists():
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            destination = DOCUMENTS_FOLDER / (
                f"{file_path.stem}_{timestamp}{file_path.suffix}"
            )

        shutil.move(str(file_path), str(destination))

        print(f"Moved successfully: {destination}")
        notify_user(
            "PDF Automatically Moved",
            f"{destination.name} was moved to Documents.",
        )

    except (OSError, shutil.Error) as error:
        print(f"Error moving {file_path.name}: {error}")
        notify_user("Error Moving PDF", str(error))


class NewFileHandler(FileSystemEventHandler):

    def on_created(self, event):
        if not event.is_directory:
            move_pdf(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            # Downloads may finish by renaming a temporary file
            move_pdf(event.dest_path)

    def on_modified(self, event):
        if not event.is_directory:
            move_pdf(event.src_path)


if __name__ == "__main__":
    if not DOWNLOADS_FOLDER.is_dir():
        raise FileNotFoundError(
            f"Downloads folder not found: {DOWNLOADS_FOLDER}"
        )

    DOCUMENTS_FOLDER.mkdir(parents=True, exist_ok=True)

    observer = Observer()
    observer.schedule(
        NewFileHandler(),
        str(DOWNLOADS_FOLDER),
        recursive=False,
    )

    observer.start()

    print("Folder Monitor is running.")
    print(f"Watching: {DOWNLOADS_FOLDER}")
    print(f"PDF destination: {DOCUMENTS_FOLDER}")
    print("Download a NEW PDF to test. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping Folder Monitor...")
        observer.stop()
    finally:
        observer.join()
