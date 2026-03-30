from Jarvis import Jarvis
from jarvis_system import stop_recording

def main():
    jarvis = Jarvis()
    try:
        jarvis.jarvis_loop()
    finally:
        stop_recording()

if __name__ == '__main__':
    main()




# We gunna need a websocket to communicate with jarvis if we want it on an Arduino eventually



