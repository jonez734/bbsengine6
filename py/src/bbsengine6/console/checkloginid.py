import dbus

def display_user(username):
    try:
        # Connect to the system bus
        system_bus = dbus.SystemBus()

        # Access the AccountsService interface
        accounts_service = system_bus.get_object('org.freedesktop.Accounts', '/org/freedesktop/Accounts')
        accounts_interface = dbus.Interface(accounts_service, 'org.freedesktop.Accounts')

        # Find the user by name
        user_path = accounts_interface.FindUserByName(username)

        # Get the user object
        user_object = system_bus.get_object('org.freedesktop.Accounts', user_path)
        user_interface = dbus.Interface(user_object, dbus.PROPERTIES_IFACE)

        # Fetch user properties
        properties = {
            "Username": user_interface.Get("org.freedesktop.Accounts.User", "UserName"),
            "Real Name": user_interface.Get("org.freedesktop.Accounts.User", "RealName"),
            "Home Directory": user_interface.Get("org.freedesktop.Accounts.User", "HomeDirectory"),
            "Shell": user_interface.Get("org.freedesktop.Accounts.User", "Shell"),
            "Email": user_interface.Get("org.freedesktop.Accounts.User", "Email"),
            "Account Enabled": user_interface.Get("org.freedesktop.Accounts.User", "Enabled"),
        }

        # Display the user's information
        print(f"User '{username}' found:")
        for key, value in properties.items():
            print(f"  {key}: {value}")

    except dbus.DBusException as e:
        # Handle the case where the user is not found
        if "org.freedesktop.Accounts.Error.UserDoesNotExist" in e.get_dbus_name():
            print(f"Error: User '{username}' does not exist.")
        else:
            print(f"An error occurred: {e}")

# Example usage
display_user("nonexistentuser")

#import dbus
from dbus.exceptions import DBusException

def check_user_permission():
    try:
        # Connect to the system bus
        system_bus = dbus.SystemBus()

        # Access the PolicyKit1 interface
        polkit_service = system_bus.get_object('org.freedesktop.PolicyKit1', '/org/freedesktop/PolicyKit1/Authority')
        polkit_interface = dbus.Interface(polkit_service, 'org.freedesktop.PolicyKit1.Authority')

        # The action we're checking: "org.freedesktop.accounts.lookup_user"
        action = "org.freedesktop.accounts.lookup_user"

        # Check if the current user has permission to perform this action
        subject = dbus.Array([], signature='v')  # Empty subject for current user
        result = polkit_interface.CheckAuthorizationSync(action, subject, 0)

        # Result contains a tuple: (result_code, details)
        result_code, details = result
        if result_code == 1:  # Authorized
            print("User has permission to look up other users.")
        else:
            print("User does not have permission to look up other users.")

    except DBusException as e:
        print(f"An error occurred: {e}")

# Example usage
# check_user_permission()

def change_user_shell(username, shell):
    bus = SystemBus()
    accounts = bus.get("org.freedesktop.Accounts")
    try:
        user = accounts.FindUserByName(username)
        user.Set("org.freedesktop.Accounts.User", "Shell", shell)
        print(f"Shell for {username} changed to {shell}.")
    except Exception as e:
        print(f"Error: {e}")

#change_user_shell("newuser", "/bin/bash")

def check_idle_state():
    try:
        # Connect to the system bus
        system_bus = dbus.SystemBus()

        # Access the login1 Manager
        logind = system_bus.get_object('org.freedesktop.login1', '/org/freedesktop/login1')
        manager = dbus.Interface(logind, 'org.freedesktop.login1.Manager')

        # Get all active sessions
        sessions = manager.GetSessions()

        for session in sessions:
            session_id, user_id, username, seat_id, object_path = session

            # Access the session object
            session_object = system_bus.get_object('org.freedesktop.login1', object_path)
            session_properties = dbus.Interface(session_object, dbus.PROPERTIES_IFACE)

            # Get the IdleHint property
            idle = session_properties.Get('org.freedesktop.login1.Session', 'IdleHint')
            print(f"Session {session_id} (User {username}) is idle: {idle}")

    except dbus.DBusException as e:
        print(f"An error occurred: {e}")

# Example usage
#check_idle_state()


#import dbus

def get_active_sessions():
    try:
        # Connect to the system bus
        bus = dbus.SystemBus()

        # Access the systemd-logind Manager interface
        login1_manager = bus.get_object('org.freedesktop.login1', '/org/freedesktop/login1')
        login1_interface = dbus.Interface(login1_manager, 'org.freedesktop.login1.Manager')

        # Get a list of sessions
        sessions = login1_interface.ListSessions()

        # Display session details
        for session in sessions:
            session_id, uid, user_name, seat, session_type = session
            print(f"Session ID: {session_id}")
            print(f"User ID: {uid}")
            print(f"User Name: {user_name}")
            print(f"Seat: {seat}")
            print(f"Session Type: {session_type}")
            print("-" * 40)

    except dbus.DBusException as e:
        print(f"DBus Error: {e}")

if __name__ == "__main__":
    # get_active_sessions()
    # check_idle_state()
    check_idle_state()

