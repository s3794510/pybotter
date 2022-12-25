# This is sample template that have the required function calls (**) to run the bot

from pybot import PyBot

def main():

    # Start program text
    print("""Hold shift + ESC to stop
Hold shift + P to pause/unpause.
Hold shift + F to show FPS
Program is running.
    """)

    # Change path of the system
    #os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # (**) Type the exact name of the window
    window_name = "The name of the target window"

    # Debug mode: show screen shot of the target window
    debug = None
    #debug = 'debug' 
    
    # (**) Initialise the bot
    bot = PyBot(window_name, debug)

    # Resize the target window
    #bot.resize(640,380)

    # (**) Run the bot
    # (**) To modify the bot actions, modify the function __actions__ in BotHandler class
    bot.run()
    

    # Exit program text
    print('Program is closed.')
    i = input("Press any key to end program.\n")


# Driver code
if __name__ == '__main__':
    main()