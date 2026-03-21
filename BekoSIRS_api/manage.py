#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    if 'runserver' in sys.argv:
        try:
            import socket
            import re
            
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Update api.ts
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            api_file = os.path.join(base_dir, 'BekoSIRS_Frontend', 'services', 'api.ts')
            
            if os.path.exists(api_file):
                with open(api_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace the COMPUTER_IP line
                new_content = re.sub(
                    r"const COMPUTER_IP = '[^']+';", 
                    f"const COMPUTER_IP = '{local_ip}';", 
                    content
                )
                
                if new_content != content:
                    with open(api_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"\n✅ Auto-updated Frontend API IP to: {local_ip} in api.ts\n")
                elif local_ip not in content:
                    print(f"\n⚠️ Could not find COMPUTER_IP string to replace in api.ts\n")
        except Exception as e:
            print(f"\n⚠️ Failed to auto-update frontend IP: {e}\n")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekosirs_backend.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
