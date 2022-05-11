from django.utils import timezone
import os


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', '_14Finger.settings')
    now = timezone.now()

    print(now)


if __name__ == '__main__':
    main()