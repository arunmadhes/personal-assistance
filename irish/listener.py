from voice_input import listen
from agent import process_command

def run_listener_loop():

    print("Listener started")

    while True:

        command = listen()

        if command:

            print("You:", command)

            response = process_command(command)

            print("Irish:", response)