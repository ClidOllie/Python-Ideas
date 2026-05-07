import sys
import time
                # For 10 rotations, use spinner_animation(4). 
                # For 25 rotations, use spinner_animation(10).
                # Faster: time.sleep(0.05) doubles the rotations.
                # Slower: time.sleep(0.2) halves the rotations.
def spinner_animation(duration=5):
    # Use a context manager or manual escape codes to hide/show the cursor
    sys.stdout.write("\033[?25l") # Hide cursor
    
    chars = ['|', '/', '-', '\\']
    end_time = time.time() + duration
    i = 0
    
    try:
        while time.time() < end_time:
            sys.stdout.write(f"\r{chars[i % len(chars)]}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
    finally:
        # Ensure the cursor is restored even if the user hits Ctrl+C
        sys.stdout.write("\r \033[?25h\n") 
        sys.stdout.flush()

if __name__ == "__main__":
    spinner_animation(3)




    


