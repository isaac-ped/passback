#!/usr/bin/env python3
import iterm2

def new_window(command):

    async def main(connection):
        app = await iterm2.async_get_app(connection)

        # Foreground the app
        await app.async_activate()

        # This will run 'vi' from bash. If you use a different shell, you'll need
        # to change it here. Running it through the shell sets up your $PATH so you
        # don't need to specify a full path to the command.
        window = await iterm2.Window.async_create(connection)
        session = window.current_tab.current_session
        await session.async_send_text(command+'\n')


    # Passing True for the second parameter means keep trying to
    # connect until the app launches.
    iterm2.run_until_complete(main, True)

def new_split(command, vertical=True):

    async def main(connection):
        app = await iterm2.async_get_app(connection)
        pane = await app.current_window.current_tab.current_session.async_split_pane(vertical=vertical)
        await pane.async_send_text(command + '\n')

    # Passing True for the second parameter means keep trying to
    # connect until the app launches.
    iterm2.run_until_complete(main, True)
